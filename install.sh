#!/bin/bash
set -ex

FFMPEG_VERSION="4.2.1"

cd /opt

yum install -y git python3 opus
if [ ! -x "$(command -v poetry)" ]; then
    curl -sSL https://install.python-poetry.org | python3 -
fi

export PATH="/root/.local/bin:$PATH"
POETRY="/root/.local/bin/poetry"
$POETRY config virtualenvs.create false

if [ ! -x "$(command -v ffmpeg)" ]; then
    mkdir -p /usr/local/bin/ffmpeg
    cd /usr/local/bin/ffmpeg
    wget https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-${FFMPEG_VERSION}-amd64-static.tar.xz
    tar xvf ffmpeg-${FFMPEG_VERSION}-amd64-static.tar.xz
    mv ffmpeg-${FFMPEG_VERSION}-amd64-static/ffmpeg .
    ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg
    cd -
fi

git clone https://github.com/ron96G/discordbot.git --branch main || true
cd /opt/discordbot
$POETRY install
chmod +x discordbot/__main__.py

cat > /etc/systemd/system/discordbot.service << EOF
[Unit]
SourcePath=/opt/discordbot
[Service]
Environment="DISCORD_SECRET_TOKEN=<secret-token>"
Environment="YOUTUBE_API_KEY=<secret-token>"
Environment="SPOTIFY_CLIENT_ID=<secret-token>"
Environment="SPOTIFY_CLIENT_SECRET=<secret-token>"
Environment="CONFIGFILE=/opt/discordbot/discordbot_config.json"
ExecStart=/opt/discordbot/discordbot/__main__.py
EOF

systemctl enable discordbot.service
systemctl start discordbot.service
systemctl status discordbot.service