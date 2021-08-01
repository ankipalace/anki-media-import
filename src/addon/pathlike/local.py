from hashlib import md5
from typing import Generator, Union
from pathlib import Path

from .base import PathLike


class LocalPath(PathLike):
    path: Path

    def __init__(self, path: Union[str, Path]) -> None:
        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path

    def is_file(self) -> bool:
        return self.path.is_file()

    def is_dir(self) -> bool:
        return self.path.is_dir()

    def iterdir(self) -> Generator["LocalPath", None, None]:
        for path in self.path.iterdir():
            yield LocalPath(path)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def data(self) -> bytes:
        return self.path.read_bytes()

    @property
    def extension(self) -> str:
        """Removes initial '.' """
        return self.path.suffix[1:]

    @property
    def md5(self) -> str:
        return md5(self.data).hexdigest()
