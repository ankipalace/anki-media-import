from hashlib import md5
from typing import List, Union, Optional
from pathlib import Path

from .base import RootPath, FileLike


class LocalRoot(RootPath):
    path: Path
    files: List["FileLike"]

    def __init__(self, path: Union[str, Path], recursive: bool = True) -> None:
        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path
        self.files = self.list_files(recursive=recursive)

    def list_files(self, recursive: bool) -> List["FileLike"]:
        files: List["FileLike"] = []
        self.search_files(files, self.path, recursive)
        return files

    def search_files(self, files: List["FileLike"], src: Path, recursive: bool) -> None:
        for path in src.iterdir():
            if path.is_file():
                if len(path.suffix) > 1 and self.has_media_ext(path.suffix[1:]):
                    files.append(LocalFile(path))
            elif recursive and path.is_dir():
                self.search_files(files, path, recursive=True)


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

    def is_identical(self, file: FileLike) -> bool:
        try:
            return file.size == self.size and file.md5 == self.md5  # type: ignore
        except AttributeError:
            return file.size == self.size
