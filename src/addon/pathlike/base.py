from abc import ABC, abstractmethod
from typing import Iterable


class PathLike(ABC):

    @abstractmethod
    def is_file(self) -> bool:
        pass

    @abstractmethod
    def is_dir(self) -> bool:
        pass

    @abstractmethod
    def iterdir(self) -> Iterable["PathLike"]:
        pass

    @abstractmethod
    def to_file(self) -> "FileLike":
        pass


class FileLike(ABC):
    key: str  # A string that can identify the file
    name: str
    extension: str
    size: float

    @property
    @abstractmethod
    def md5(self) -> str:
        pass

    @abstractmethod
    def read_bytes(self) -> bytes:
        pass
