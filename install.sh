#!/bin/bash
(( EUID == 0 )) || { echo "This script needs to be run as root."; exit 1; }

set -v

install -m700 ./snapper2borg.sh /usr/local/bin/
install -m644 ./snapper2borg.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable snapper2borg.service
systemctl status snapper2borg.service
