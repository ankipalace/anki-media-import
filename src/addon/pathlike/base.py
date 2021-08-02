from abc import ABC, abstractmethod
from typing import Any, List, Tuple

import aqt.editor


MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio


class RootPath(ABC):

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any):
        """Raises an Exception if the path is not valid."""
        pass

    def is_media_ext(self, extension: str) -> bool:
        return extension.lower() in MEDIA_EXT

    @abstractmethod
    def list_files(self, recursive: bool) -> List["FileLike"]:
        pass


class FileLike(ABC):
    id: str  # A string that can identify the file
    name: str
    extension: str
    size: float

    @abstractmethod
    def read_bytes(self) -> bytes:
        pass

    def is_identical(self, file: "FileLike") -> bool:
        """Returns True if its contents seems the same. 
        Does not check if the names are identical."""
        pass
