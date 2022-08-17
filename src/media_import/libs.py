import sys
import zipfile
import os
import platform
from tempfile import TemporaryDirectory
from pathlib import Path
import shutil

# https://docs.python.org/3/library/platform.html#platform.architecture
IS_64BITS = sys.maxsize > 2**32
LIBS_DIR = Path(__file__).parent / "libs"


def install_pycrypto() -> None:
    pycrypto_base = "pycryptodome-3.10.1-cp35-abi3-{}{}.whl"

    if sys.platform.startswith("linux"):
        if IS_64BITS:
            pycrypto_name = pycrypto_base.format("manylinux1", "_x86_64")
        else:
            pycrypto_name = pycrypto_base.format("manylinux1", "_i686")
    elif sys.platform.startswith("darwin"):
        if platform.processor() == "arm":
            pycrypto_name = pycrypto_base.format("macosx_12_0", "_arm64")
        else:
            pycrypto_name = pycrypto_base.format("macosx_10_9", "_x86_64")
    elif sys.platform.startswith("win32"):
        if IS_64BITS:
            pycrypto_name = pycrypto_base.format("win", "_amd64")
        else:
            pycrypto_name = pycrypto_base.format("win32", "")

    pycrypto_path = Path(__file__).parent / "pycryptodome" / pycrypto_name

    with zipfile.ZipFile(pycrypto_path) as zfile:
        zfile.extractall(LIBS_DIR)
    print("Successfully installed pycryptodome for Media Import")


def uninstall_pycrypto() -> None:
    """On Windows, deleting crypto dir may throw an error as .pyd file is open.
    In that case move(rename) the folder into %TEMP%
    which may be cleaned up later by the os/user.
    """
    pycrypto_path = LIBS_DIR / "Crypto"
    try:
        shutil.rmtree(pycrypto_path)
    except PermissionError:
        shutil.rmtree(pycrypto_path, ignore_errors=True)  # remove as much as possible
        tmpdir = TemporaryDirectory()
        dest_path = Path(tmpdir.name) / "Crypto"
        os.rename(pycrypto_path, dest_path)
        try:
            tmpdir.cleanup()
        except:
            pass
