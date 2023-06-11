import os
import platform
import shutil
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

LIBS_DIR = Path(__file__).parent / "libs"
ZSTANDARD_WHEELS_DIR = LIBS_DIR / "zstandard_wheels"

# https://docs.python.org/3/library/platform.html#platform.architecture
IS_64BITS = sys.maxsize > 2**32
ARCHITECTURE = platform.machine()


def install_zstandard() -> None:
    if sys.version_info[:2] != (3, 9):
        print("Media Import: Cant install zstandard, python version is not 3.9")
        return

    zstd_path = ZSTANDARD_WHEELS_DIR / _zstandard_wheel_name()
    with zipfile.ZipFile(zstd_path) as zfile:
        zfile.extractall(LIBS_DIR)
    print("Successfully installed zstandard for Media Import")


def uninstall_zstandard() -> None:
    """On Windows, deleting the package dir may throw an error as .pyd file is open.
    In that case move(rename) the folder into %TEMP%
    which may be cleaned up later by the os/user.
    """
    zstandard_files = LIBS_DIR.glob("zstandard*")
    for file in zstandard_files:
        try:
            if file.is_file():
                file.unlink()
            else:
                shutil.rmtree(file)
        except PermissionError:
            if file.is_dir():
                shutil.rmtree(file, ignore_errors=True)  # remove as much as possible
            tmpdir = TemporaryDirectory()
            os.rename(file, Path(tmpdir.name) / file.name)
            try:
                tmpdir.cleanup()
            except:
                pass


def _zstandard_wheel_name() -> str:
    zstd_base = "zstandard-0.21.0-cp39-cp39-{}.whl"
    if sys.platform.startswith("linux"):
        arch = platform.machine()
        if arch == "x86_64":
            zstd_name = zstd_base.format("manylinux_2_17_x86_64.manylinux2014_x86_64")
        elif arch == "i686":
            zstd_name = zstd_base.format(
                "manylinux_2_5_i686.manylinux1_i686.manylinux_2_17_i686.manylinux2014_i686",
            )
        elif arch == "aarch64":
            zstd_name = zstd_base.format("manylinux_2_17_aarch64.manylinux2014_aarch64")
        else:
            raise ValueError(f"Unsupported architecture: {arch}")
    elif sys.platform.startswith("darwin"):
        if platform.processor() == "arm":
            zstd_name = zstd_base.format("macosx_11_0_arm64")
        else:
            zstd_name = zstd_base.format("macosx_10_9_x86_64")
    elif sys.platform.startswith("win32"):
        if IS_64BITS:
            zstd_name = zstd_base.format("win_amd64")
        else:
            zstd_name = zstd_base.format("win32")
    return zstd_name
