#!/usr/bin/env sh
PODMAN_URI=$(sed -n 's/^podman_uri = \(.*\)/\1/p' "$DOCLEANER_CONF")
PODMAN_SOCKET=$(echo "$PODMAN_URI" | sed 's|.*://||')
PODMAN_NESTED_SOCK="unix:///home/podman/nested_podman.sock"

if [ "$PODMAN_URI" = "$PODMAN_NESTED_SOCK" ]; then
  echo "[*] Launching podman serving /home/podman/nested_podman.sock for nested containers"
  podman system service -t 0 "$PODMAN_NESTED_SOCK" &
  echo "[*] Loading plugins"
  for plugin in /opt/plugins/*; do
    podman load -i "$plugin"
    echo "[*] Plugin registered: $plugin"
  done
fi

if [ ! -S "$PODMAN_SOCKET" ]; then
  echo "[!] Socket not found: $PODMAN_SOCKET"
  exit 1
fi

echo "[*] Using Podman socket $PODMAN_URI"
echo "[*] Serving web application at ${DOCLEANER_URL}"
/opt/venv/bin/uvicorn --host 0.0.0.0 --port 8080 --no-access-log docleaner.api.entrypoints.web.main:app
