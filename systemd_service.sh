#!/bin/bash

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BOT_USER="$(whoami)"
VENV_PYTHON="$BOT_DIR/venv/bin/python"
SERVICE_NAME="muzovkantv2"

echo "creating systemd service for user '$BOT_USER' in '$BOT_DIR'..."

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=muzovkantv2 discord bot
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
ExecStart=$VENV_PYTHON $BOT_DIR/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "done. status:"
sudo systemctl status $SERVICE_NAME
