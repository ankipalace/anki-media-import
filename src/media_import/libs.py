import sys
import zipfile
from pathlib import Path

# https://docs.python.org/3/library/platform.html#platform.architecture
IS_64BITS = sys.maxsize > 2**32


def install_pycrypto() -> None:
    pycrypto_base = "pycryptodome-3.10.1-cp35-abi3-{}{}.whl"

    if sys.platform.startswith("linux"):
        if IS_64BITS:
            pycrypto_name = pycrypto_base.format("manylinux1", "_x86_64")
        else:
            pycrypto_name = pycrypto_base.format("manylinux1", "_i686")
    elif sys.platform.startswith("darwin"):
        pycrypto_name = pycrypto_base.format("macosx_10_9", "_x86_64")
    elif sys.platform.startswith("win32"):
        if IS_64BITS:
            pycrypto_name = pycrypto_base.format("win", "_amd64")
        else:
            pycrypto_name = pycrypto_base.format("win32", "")

    pycrypto_path = Path(__file__).parent / "pycryptodome" / pycrypto_name
    libs_path = Path(__file__).parent / "libs"
    dist_info_name = "pycryptodome-3.10.1.dist-info"

    with zipfile.ZipFile(pycrypto_path) as zfile:
        zfile.extractall(libs_path)
    print("Successfully installed pycryptodome for Media Import")
