import os
import tarfile
from tempfile import TemporaryDirectory
from typing import List, Tuple

from podman import PodmanClient  # type: ignore

from docleaner.api.services.sandbox import Sandbox


class ContainerizedSandbox(Sandbox):
    """Launches a podman-controlled container with a predefined image.
    That container is expected to idle (e.g. via 'sleep infinity') after startup.
    This sandbox will then copy the source file into the container's filesystem (via the podman API),
    execute '/opt/process <source_path> <result_path>', retrieve and return the result."""

    def __init__(self, container_image: str, podman_uri: str):
        self._image = container_image
        self._podman_uri = podman_uri

    async def process(self, source: bytes) -> Tuple[List[str], bool, bytes]:
        with PodmanClient(
            base_url=self._podman_uri
        ) as podman, TemporaryDirectory() as tmpdir:
            log = []
            result = b""
            success = False
            source_path = os.path.join(tmpdir, "source")
            source_tar = os.path.join(tmpdir, "source.tar")
            with open(source_path, "wb") as f:
                f.write(source)
            with tarfile.open(source_tar, "w") as tar:
                tar.add(source_path, arcname="source")
            container = podman.containers.create(image=self._image, auto_remove=True)
            container.start()
            with open(source_tar, "rb") as tar_raw:
                container.put_archive("/tmp", tar_raw)
            process_status, process_out = container.exec_run(
                ["/opt/process", "/tmp/source", "/tmp/result"]
            )
            log.append(process_out.decode("utf-8"))
            if process_status == 0:
                result_iterator, _ = container.get_archive("/tmp/result")
                result = b"".join(result_iterator)
                success = True
            container.stop(timeout=10)
            return log, success, result
