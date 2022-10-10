import os
from typing import Any, Dict, Optional

import boto3

client = boto3.client("s3")

BUCKET_NAME = os.environ.get("CONFIG_BUCKET_NAME", "discordbot-config.bottich")
DEFAULT_VERSION = "v1"


class ConfigStore:
    config: Dict[str, str]

    def __init__(self, config: Optional[Dict[str, str]] = None):
        self.config = config or {}

    def get(self, key: str, fallback_env: bool = True, fallback: str = None):
        val = self.config.get(key)
        if val is None and fallback_env:
            val = os.environ.get(key)
        return val or fallback

    def get_env_first(self, key: str, fallback: str = None):
        val = os.environ.get(key)
        if val is None:
            val = self.config.get(key)
        return val or fallback

    def getAll(self):
        return self.config

    @classmethod
    def s3(cls, version: str = DEFAULT_VERSION):
        config = load_s3_config(version)
        return cls(config)

    @classmethod
    def env_file(cls, path: str = ".env"):
        with open(path, "r") as f:
            content = load_env_file(f.read())
        return cls(content)

    def set_in_env(self):
        os_set_dict(self.config)


def load_env_file(content: str):
    values = {}

    for line in content.splitlines(keepends=False):
        if line.startswith("#") or not line.strip():
            # ignore comments and empty lines
            continue
        key, val, *_ = line.split("=")

        values[key.strip()] = val.strip()

    return values


def os_set_dict(dict: Dict[str, str]):
    for key, val in dict.items():
        os.environ[key] = val


def load_s3_config(version: Optional[str] = None) -> Dict[str, str]:
    version = version or DEFAULT_VERSION
    obj = client.get_object(Bucket=BUCKET_NAME, Key=f"{version}/.env")

    raw: str = obj["Body"].read().decode("utf-8")
    return load_env_file(raw)


if __name__ == "__main__":
    config: ConfigStore = ConfigStore.s3()
    print(config.getAll())

    config1: ConfigStore = ConfigStore.env_file(path="/mnt/d/PROJECTS/discordbot/.env")
    print(config1.get("TWITCH_CLIENT_ID"))
