import asyncio
import json
import os
import tarfile
import traceback
from tempfile import TemporaryDirectory
from typing import Any, Dict

from podman import PodmanClient  # type: ignore
from podman.errors.exceptions import APIError as PodmanAPIError  # type: ignore
from podman.domain.containers import Container  # type: ignore

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
            metadata_result: Dict[str, Dict[str, Any]] = {"primary": {}, "embeds": {}}
            metadata_src: Dict[str, Dict[str, Any]] = {"primary": {}, "embeds": {}}
            success = False
            # Copy source into container
            source_path = os.path.join(tmpdir, "source")
            source_tar = os.path.join(tmpdir, "source.tar")
            with open(source_path, "wb") as f:
                f.write(source)
            with tarfile.open(source_tar, "w") as tar:
                tar.add(source_path, arcname="source")
                try:
                    container = podman.containers.create(
                        image=self._image, auto_remove=True, network_mode="none"
                    )
                except PodmanAPIError:
                    return SandboxResult(
                        success=success,
                        log=[f"Invalid container image {self._image}"],
                        result=result_document,
                        metadata_result=metadata_result,
                        metadata_src=metadata_src,
                    )
            container.start()
            with open(source_tar, "rb") as tar_raw:
                container.put_archive("/tmp", tar_raw)
            try:
                # Pre-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/source", "/tmp/meta_src"]
                )
                if process_status != 0:
                    log.append(process_out.decode("utf-8"))
                    raise ValueError()
                # Metadata processing
                process_status, process_out = container.exec_run(
                    ["/opt/process", "/tmp/source", "/tmp/result"]
                )
                log.append(process_out.decode("utf-8"))
                if process_status != 0:
                    raise ValueError()
                # Post-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/result", "/tmp/meta_result"]
                )
                if process_status != 0:
                    log.append(process_out.decode("utf-8"))
                    raise ValueError()
                # Retrieve result from container
                result_document = self._retrieve_file("/tmp/result", container, tmpdir)
                metadata_src = json.loads(
                    self._retrieve_file("/tmp/meta_src", container, tmpdir)
                )
                metadata_result = json.loads(
                    self._retrieve_file("/tmp/meta_result", container, tmpdir)
                )
                success = True
            except ValueError:
                traceback.print_exc()
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

    @staticmethod
    def _retrieve_file(path: str, container: Container, tmpdir: str) -> bytes:
        """Retrieves and returns a file by its path from a running container."""
        result_iterator, _ = container.get_archive(path)
        result_tar_raw = b"".join(result_iterator)
        result_tar = os.path.join(tmpdir, "retrieval.tar")
        with open(result_tar, "wb") as f:
            f.write(result_tar_raw)
        with tarfile.open(result_tar, "r") as tar:
            tar.extract(os.path.basename(path), path=tmpdir)
        with open(os.path.join(tmpdir, os.path.basename(path)), "rb") as f:
            return f.read()
