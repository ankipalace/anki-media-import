from hashlib import md5
from typing import Generator, Union, Optional
from pathlib import Path

from .base import FileLike, PathLike


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

    def to_file(self) -> "LocalFile":
        return LocalFile(self.path)


class LocalFile(FileLike):
    key: str  # == str(path)
    name: str
    extension: str
    size: float

    _md5: Optional[str]
    path: Path

    def __init__(self, path: Path):
        self.key = str(path)
        self.name = path.name
        self.extension = path.suffix[1:]
        self.size = path.stat().st_size
        self.path = path
        self._md5 = None

    @property
    def md5(self) -> str:
        if not self._md5:  # Cache result
            self._md5 = md5(self.read_bytes()).hexdigest()
        return self._md5

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()
