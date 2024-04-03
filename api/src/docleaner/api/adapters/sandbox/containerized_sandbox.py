import asyncio
from dataclasses import asdict
import json
import logging
import os
import tarfile
import traceback
from tempfile import TemporaryDirectory
from typing import Any, Dict, Union

from podman import PodmanClient  # type: ignore
from podman.errors.exceptions import APIError as PodmanAPIError  # type: ignore
from podman.domain.containers import Container  # type: ignore

from docleaner.api.core.job import JobParams
from docleaner.api.core.sandbox import Sandbox, SandboxResult

logger = logging.getLogger(__name__)


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
        logger.info(
            "Containerized sandbox with image %s via %s is ready",
            self._image,
            self._podman_uri,
        )

    async def process(self, source: bytes, params: JobParams) -> SandboxResult:
        """Runs _process_blocking() in its own thread due to blocking dependencies (podman)."""
        return await asyncio.to_thread(self._process_blocking, source, params)

    def _process_blocking(self, source: bytes, params: JobParams) -> SandboxResult:
        with PodmanClient(
            base_url=self._podman_uri
        ) as podman, TemporaryDirectory() as tmpdir:
            log = []
            result_document = b""
            metadata_result: Dict[str, Union[bool, Dict[str, Any]]] = {
                "primary": {},
                "embeds": {},
                "signed": False,
            }
            metadata_src: Dict[str, Union[bool, Dict[str, Any]]] = {
                "primary": {},
                "embeds": {},
                "signed": False,
            }
            success = False
            # Copy source and params into container
            source_path = os.path.join(tmpdir, "source")
            params_path = os.path.join(tmpdir, "params")
            source_tar = os.path.join(tmpdir, "source.tar")
            logger.debug("Writing temporary source file to %s", source_path)
            with open(source_path, "wb") as f:
                f.write(source)
            logger.debug("Writing temporary params to %s", params_path)
            with open(params_path, "w") as f:
                f.write(json.dumps(asdict(params)))
            logger.debug("Writing temporary source archive to %s", source_tar)
            with tarfile.open(source_tar, "w") as tar:
                tar.add(source_path, arcname="source")
                tar.add(params_path, arcname="params")
            try:
                container = podman.containers.create(
                    image=self._image, auto_remove=True, network_mode="none"
                )
            except PodmanAPIError:
                logger.warning(
                    f"Could not create container for {self._image}:\n{traceback.format_exc()}"
                )
                return SandboxResult(
                    success=success,
                    log=[f"Invalid container image {self._image}"],
                    result=result_document,
                    metadata_result=metadata_result,
                    metadata_src=metadata_src,
                )
            logger.debug("Starting container %s", container.name)
            container.start()
            logger.debug("Copying %s into container %s", source_tar, container.name)
            with open(source_tar, "rb") as tar_raw:
                container.put_archive("/tmp", tar_raw)
            try:
                # Pre-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/source", "/tmp/meta_src", "/tmp/params"]
                )
                if process_status != 0:
                    log.append(process_out.decode("utf-8"))
                    raise ValueError()
                # Metadata processing
                process_status, process_out = container.exec_run(
                    ["/opt/process", "/tmp/source", "/tmp/result", "/tmp/params"]
                )
                log.append(process_out.decode("utf-8"))
                if process_status != 0:
                    raise ValueError()
                # Post-process metadata analysis
                process_status, process_out = container.exec_run(
                    ["/opt/analyze", "/tmp/result", "/tmp/meta_result", "/tmp/params"]
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
                result_document = b""
                logger.warning(
                    f"Exception in containerized_sandbox.process():\n{traceback.format_exc()}"
                )
            finally:
                logger.debug("Stopping container %s", container.name)
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
