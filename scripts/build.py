from pathlib import Path

import _aqt
import anki
import subprocess


def vendor_requirements():
    """Install requirements into the src/media_import/libs directory."""
    subprocess.run(
        [
            "pip",
            "install",
            "--no-deps",
            "--target=./src/media_import/libs",
            "-r",
            "requirements.txt",
        ],
        check=True,
    )

def create_init_file(module):
    module_path = Path(module.__path__[0])
    init_file_path = module_path / "__init__.py"
    init_file_path.touch(exist_ok=True)
    

if __name__ == "__main__":
    vendor_requirements()

    # This makes mypy type checking work on Anki versions >= 2.1.55
    create_init_file(anki)
    create_init_file(_aqt)
