#!/bin/bash
set -e
yum install -y git python3 opus


cd /opt

git clone https://github.com/ron96G/discordbot.git --branch main || true
cd discordbot
pip3 install --upgrade -r requirements.txt
chmod +x main.py

mkdir -p /usr/local/bin/ffmpeg
cd /usr/local/bin/ffmpeg
wget https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-4.2.1-amd64-static.tar.xz
tar xvf ffmpeg-4.2.1-amd64-static.tar.xz
mv ffmpeg-4.2.1-amd64-static/ffmpeg .
ln -s /usr/local/bin/ffmpeg/ffmpeg /usr/bin/ffmpeg
cd -

cat > /etc/systemd/system/discordbot.service << EOF
[Unit]
SourcePath=/opt/discordbot
[Service]
Environment="DISCORD_SECRET_TOKEN=<secret-token>"
Environment="YOUTUBE_API_KEY=<secret-token>"
ExecStart=/opt/discordbot/main.py
EOF

systemctl enable discordbot.service
systemctl start discordbot.service
systemctl status discordbot.service