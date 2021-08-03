try:
    import Crypto
except:
    from . import install_libs


import sys
from pathlib import Path
core_dir = Path(__file__).resolve().parent / "core"
sys.path.append(str(core_dir))
libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))


from . import ui