import sys
import shutil
from pathlib import Path

# https://docs.python.org/3/library/platform.html#platform.architecture
is_64bits = sys.maxsize > 2**32

pycrypto_base = "pycryptodome-3.10.1-cp35-abi3-{}_{}"

if sys.platform.startswith("linux"):
    if is_64bits:
        pycrypto_folder = pycrypto_base.format("manylinux1", "x86_64")
    else:
        pycrypto_folder = pycrypto_base.format("manylinux1", "i686")
elif sys.platform.startswith("darwin"):
    pycrypto_folder = pycrypto_base.format("macosx_10_9", "x86_64")
elif sys.platform.startswith("win32"):
    if is_64bits:
        pycrypto_folder = pycrypto_base.format("win", "amd64")
    else:
        pycrypto_folder = pycrypto_base.format("win32", "")[:-1]

pycrypto_path = Path(__file__).parent / "pycryptodome" / pycrypto_folder
libs_path = Path(__file__).parent / "libs"
dist_info_name = "pycryptodome-3.10.1.dist-info"

shutil.copytree(str(pycrypto_path / "Crypto"), str(libs_path / "Crypto"))
shutil.copytree(str(pycrypto_path / dist_info_name),
                str(libs_path / dist_info_name))
