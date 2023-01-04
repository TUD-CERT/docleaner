#!/usr/bin/env sh
pip3 install -r /srv/requirements/development.txt
pip3 install -e /srv
npm --prefix /srv install
echo "Development environment is ready"
sleep infinity
