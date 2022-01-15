#!/bin/bash
set -e
yum install -y git python3 opus
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

cd /opt

git clone https://github.com/ron96G/discordbot.git --branch main || true
cd discordbot
poetry install
source $HOME/.poetry/env

chmod +x main.py

if [ ! -x "$(command -v ffmpeg)" ]; then
    mkdir -p /usr/local/bin/ffmpeg
    cd /usr/local/bin/ffmpeg
    wget https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-4.2.1-amd64-static.tar.xz
    tar xvf ffmpeg-4.2.1-amd64-static.tar.xz
    mv ffmpeg-4.2.1-amd64-static/ffmpeg .
    ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg
    cd -
fi

cat > /etc/systemd/system/discordbot.service << EOF
[Unit]
SourcePath=/opt/discordbot
[Service]
Environment="DISCORD_SECRET_TOKEN=<secret-token>"
Environment="YOUTUBE_API_KEY=<secret-token>"
Environment="SPOTIFY_CLIENT_ID=<secret-token>"
Environment="SPOTIFY_CLIENT_SECRET=<secret-token>"
Environment="CONFIGFILE=/opt/discordbot/discordbot_config.json"
ExecStart=/opt/discordbot/__main__.py
EOF

systemctl enable discordbot.service
systemctl start discordbot.service
systemctl status discordbot.service