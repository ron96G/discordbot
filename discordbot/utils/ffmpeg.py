import os
import tarfile
from shutil import which
from subprocess import PIPE, Popen

import requests


def is_ffmpeg_installed():
    return which("ffmpeg") is not None


def create_link(src_path: str, dst_path: str):
    if is_ffmpeg_installed():
        safe_unlink(dst_path)
    os.symlink(src_path, dst_path)


def safe_unlink(path: str):
    try:
        os.unlink(path)
    except:
        pass


def rm(path: str):
    try:
        os.remove(path)
    except:
        pass


def get_installed_version() -> str:
    proc = Popen("ffmpeg", stdout=PIPE, stderr=PIPE)
    # Only need first 20 bytes to get version
    output = proc.stderr.read(20)
    version = output[-5:].decode("utf-8")
    return version


def install(version: str, force=False):

    FFMPEG_DOWNLOAD_URL = f"https://johnvansickle.com/ffmpeg/releases/ffmpeg-{version}-amd64-static.tar.xz"
    LOCAL_PATH = f"/usr/local/bin"
    FFMPEG_TAR_PATH = f"{LOCAL_PATH}/ffmpeg-{version}-amd64-static.tar.xz"
    FFMPEG_LOCAL_PATH = f"{LOCAL_PATH}/ffmpeg-{version}-amd64-static"
    FFMPEG_LOCAL_BIN_PATH = f"{FFMPEG_LOCAL_PATH}/ffmpeg"
    FFMPEG_BIN_PATH = "/usr/bin/ffmpeg"

    installed_version = None
    if is_ffmpeg_installed():
        installed_version = get_installed_version()

    if not force and installed_version == version:
        print(f"Version {version} is already installed. Use force=true to overwrite...")
        return False

    response = requests.get(FFMPEG_DOWNLOAD_URL)

    if response.status_code != 200:
        print(f"Failed to download {FFMPEG_DOWNLOAD_URL} with {response.status_code}")
        return False

    rm(FFMPEG_TAR_PATH)
    open(FFMPEG_TAR_PATH, "wb").write(response.content)

    if os.path.exists(FFMPEG_LOCAL_PATH):
        print(f"Version {version} already exists. Removing...")
        safe_unlink(FFMPEG_BIN_PATH)
        rm(FFMPEG_LOCAL_PATH)

    tar = tarfile.open(FFMPEG_TAR_PATH)
    tar.extractall(path=LOCAL_PATH)
    tar.close()

    create_link(FFMPEG_LOCAL_BIN_PATH, FFMPEG_BIN_PATH)

    rm(FFMPEG_TAR_PATH)
    return is_ffmpeg_installed()


if __name__ == "__main__":
    if install():
        print(f"Successfully installed ffmpeg")
    else:
        print(f"Failed to install ffmpeg")
