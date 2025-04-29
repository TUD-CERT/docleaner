#!/usr/bin/env sh
set -e
python3 -m venv /srv/venv
/srv/venv/bin/pip3 install -r /srv/requirements/development.txt
/srv/venv/bin/pip3 install -e /srv
echo "source /srv/venv/bin/activate" >/root/.profile
npm --prefix /srv install

if [ ! -S /run/ext_podman.sock ]; then
  echo "[*] Preparing to run nested containers, because /run/ext_podman.sock is not a socket"
  export PODMAN_SOCKET="unix:///home/podman/nested_podman.sock"
  su podman -c "podman system service -t 0 ${PODMAN_SOCKET}" &
  while [ ! -S /home/podman/nested_podman.sock ]; do sleep 1; done
  find src/docleaner/api/plugins -name Containerfile \
    -exec sh -c '
      for f do
        build_plugin "$f"
      done' sh-find '{}' \;
else
  echo "[*] Running containers via mounted socket /run/ext_podman.sock"
  export PODMAN_SOCKET="unix:///run/ext_podman.sock"
fi
sed -ire "s#podman_uri = .*#podman_uri = ${PODMAN_SOCKET}#" /etc/docleaner.conf

echo "Development environment is ready"
sleep infinity
