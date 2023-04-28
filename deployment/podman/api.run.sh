#!/usr/bin/env sh
echo "[*] Launching podman serving /home/podman/nested_podman.sock for nested containers"
podman system service -t 0 unix:///home/podman/nested_podman.sock &
echo "[*] Serving web application at ${DOCLEANER_URL}"
uvicorn --host 0.0.0.0 --port 8080 --no-access-log docleaner.api.entrypoints.web.main:app
