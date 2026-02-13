#!/bin/bash
# Setup systemd timer for MaxBitcoins on honkbox

set -e

echo "Setting up MaxBitcoins systemd timer..."

# Create service file
cat > ~/.config/systemd/user/maxbitcoins.service << 'SERVICE'
[Unit]
Description=MaxBitcoins Agent

[Service]
Type=oneshot
WorkingDirectory=%h/maxbitcoins
ExecStart=/usr/bin/docker run --rm --network host -v %h/.satmax:/data --env-file %h/maxbitcoins/.env maxbitcoins
Environment=DOCKER_HOST=unix:///run/user/1000/docker.sock

[Install]
WantedBy=default.target
SERVICE

# Create timer file
cat > ~/.config/systemd/user/maxbitcoins.timer << 'TIMER'
[Unit]
Description=MaxBitcoins every 30 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=30min
Unit=maxbitcoins.service

[Install]
WantedBy=timers.target
TIMER

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable --now maxbitcoins.timer

echo "Timer enabled. Status:"
systemctl --user list-timers --all | grep maxbitcoins
