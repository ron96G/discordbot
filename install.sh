#!/bin/bash
set -ex

cd /opt

yum install -y git python3 opus
if [ ! -x "$(command -v poetry)" ]; then
    curl -sSL https://install.python-poetry.org | python3 -
fi

export PATH="/root/.local/bin:$PATH"
POETRY="/root/.local/bin/poetry"
$POETRY config virtualenvs.create false

git clone https://github.com/ron96G/discordbot.git --branch main || true
cd /opt/discordbot
$POETRY install
chmod +x discordbot/__main__.py

cat > /etc/systemd/system/discordbot.service << EOF
[Unit]
Description=Discordbot named Bottich
After=network-online.target
Wants=network-online.target systemd-networkd-wait-online.service
SourcePath=/opt/discordbot

[Service]
Restart=always
RestartSec=5s
ExecStart=/opt/discordbot/discordbot/__main__.py
EOF

systemctl enable discordbot.service
systemctl start discordbot.service
systemctl status discordbot.service