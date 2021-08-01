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

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns file name, including its file extension. """
        pass

    @property
    @abstractmethod
    def data(self) -> bytes:
        pass

    @property
    @abstractmethod
    def extension(self) -> str:
        """Returns file extension. eg. 'png' """
        pass

    @property
    @abstractmethod
    def md5(self) -> str:
        pass
