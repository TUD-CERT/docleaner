#!/usr/bin/env sh
set -e
pip3 install -r /srv/requirements/development.txt
pip3 install -e /srv
npm --prefix /srv install

if [ ! -S /run/ext_podman.sock ]; then
  echo "[*] Preparing to run nested containers, because /run/ext_podman.sock is not a socket"
  PODMAN_SOCKET="unix:///run/nested_podman.sock"
  podman system service -t 0 ${PODMAN_SOCKET} &
  find src/docleaner/api/plugins -name Containerfile \
    -exec sh -c '
      for f do
        build_plugin "$f"
      done' sh-find '{}' \;
else
  echo "[*] Running containers via mounted socket /run/ext_podman.sock"
  PODMAN_SOCKET="unix:///run/ext_podman.sock"
fi
sed -ire "s#podman_uri = .*#podman_uri = ${PODMAN_SOCKET}#" /etc/docleaner.conf

echo "Development environment is ready"
sleep infinity
