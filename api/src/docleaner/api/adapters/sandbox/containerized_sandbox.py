import asyncio
import json
import os
import tarfile
from tempfile import TemporaryDirectory

from podman import PodmanClient  # type: ignore

from docleaner.api.services.sandbox import Sandbox, SandboxResult


class ContainerizedSandbox(Sandbox):
    """Launches a podman-controlled container with a predefined image.
    That container is expected to idle (e.g. via 'sleep infinity') after startup.
    This sandbox will then copy the source file into the container's filesystem (via the podman API),
    execute '/opt/analyze <source_path>' to retrieve source metadata,
    then execute '/opt/process <source_path> <result_path>' for metadata processing,
    then execute '/opt/analyze <result_path>' to retrieve result metadata
    and finally retrieve+return the result."""

    def __init__(self, container_image: str, podman_uri: str):
        self._image = container_image
        self._podman_uri = podman_uri

    async def process(self, source: bytes) -> SandboxResult:
        """Runs _process() in its own thread due to blocking dependencies (podman)."""
        return await asyncio.to_thread(self._process_blocking, source)

    def _process_blocking(self, source: bytes) -> SandboxResult:
        with PodmanClient(
            base_url=self._podman_uri
        ) as podman, TemporaryDirectory() as tmpdir:
            log = []
            result_document = b""
            metadata_result = metadata_src = {}
            success = False
            # Copy source into container
            source_path = os.path.join(tmpdir, "source")
            source_tar = os.path.join(tmpdir, "source.tar")
            with open(source_path, "wb") as f:
                f.write(source)
            with tarfile.open(source_tar, "w") as tar:
                tar.add(source_path, arcname="source")
                container = podman.containers.create(
                    image=self._image, auto_remove=False, network_mode="none"
                )
            container.start()
            with open(source_tar, "rb") as tar_raw:
                container.put_archive("/tmp", tar_raw)
            try:
                # Pre-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/source"]
                )
                if process_status != 0:
                    log.append(process_out.decode("utf-8"))
                    raise ValueError()
                metadata_src = json.loads(process_out.decode("utf-8"))
                # Metadata processing
                process_status, process_out = container.exec_run(
                    ["/opt/process", "/tmp/source", "/tmp/result"]
                )
                log.append(process_out.decode("utf-8"))
                if process_status != 0:
                    raise ValueError()
                # Retrieve result from container
                result_iterator, _ = container.get_archive("/tmp/result")
                result_tar_raw = b"".join(result_iterator)
                result_tar = os.path.join(tmpdir, "result.tar")
                with open(result_tar, "wb") as f:
                    f.write(result_tar_raw)
                with tarfile.open(result_tar, "r") as tar:
                    tar.extract("result", path=tmpdir)
                with open(os.path.join(tmpdir, "result"), "rb") as f:
                    result_document = f.read()
                # Post-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/result"]
                )
                if process_status != 0:
                    log.append(process_out.decode("utf-8"))
                    raise ValueError()
                metadata_result = json.loads(process_out.decode("utf-8"))
                success = True
            except ValueError:
                result_document = b""
            finally:
                container.stop(timeout=10)
                return SandboxResult(
                    success=success,
                    log=log,
                    result=result_document,
                    metadata_result=metadata_result,
                    metadata_src=metadata_src,
                )
