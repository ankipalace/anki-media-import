
import sys
from pathlib import Path
libs_dir = Path(__file__).resolve().parent / "libs"
sys.path.append(str(libs_dir))

from . import ui
from . import config
