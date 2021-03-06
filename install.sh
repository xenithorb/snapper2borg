#!/bin/bash
(( EUID == 0 )) || { echo "This script needs to be run as root."; exit 1; }

set -v

rm -v /etc/systemd/system/snapper2borg*.service

install -m700 "${0%/*}/snapper2borg.sh" /usr/local/bin/
install -m644 "${0%/*}/snapper2borg@.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable snapper2borg@.service
