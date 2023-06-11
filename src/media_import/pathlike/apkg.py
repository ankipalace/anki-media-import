import io
import json
import zipfile
from functools import cached_property
from hashlib import md5
from pathlib import Path
from typing import IO, Dict, List, Union

try:
    import zstandard
except ImportError:
    # The import of the add-on shouldn't fail if zstandard is not installed.
    print("Media Import: zstandard not installed, cannot import apkg files")


from .base import FileLike, RootPath
from .errors import IsADirectoryError, MalformedURLError, RootNotFoundError
from .media_entries_pb2 import MediaEntries  # type: ignore

# chunk size for zstd decompression
ZSTD_CHUNK_SIZE = 16384


class ApkgRoot(RootPath):
    raw: str
    name: str
    files: List["FileLike"]
    path: Path
    zip_file: zipfile.ZipFile

    def __init__(self, path: Union[str, Path]) -> None:
        self.raw = str(path)
        try:
            if isinstance(path, str):
                self.path = Path(path)
            else:
                self.path = path
            if not self.path.is_file():
                if self.path.is_dir():
                    raise IsADirectoryError()
                else:
                    raise RootNotFoundError()
            if not self.path.suffix == ".apkg":
                raise MalformedURLError()
        except OSError:
            raise MalformedURLError()
        self.name = self.path.name
        self.zip_file = zipfile.ZipFile(self.path, "r")
        self.files = self.list_files()

    def list_files(self) -> List["FileLike"]:
        # The media file contains a mapping from media filenames inside the zip file to the original filenames.
        old_to_new_name = self._media_dict()
        files: List["FileLike"] = [
            FileInZip(new, zip_path=self.path, name_in_zip=old)
            for old, new in old_to_new_name.items()
        ]
        return files

    def _media_dict(self) -> Dict[str, str]:
        try:
            # old media file format (json)
            result = json.loads(self.zip_file.read("media").decode("utf-8"))
        except UnicodeDecodeError:
            # new media file format (zstd compressed protobuf)
            file_names = _extract_file_names_from_new_media_file(
                io.BytesIO(self.zip_file.open("media").read())
            )
            result = {str(i): file_name for i, file_name in enumerate(file_names)}
        return result


def _extract_file_names_from_new_media_file(file: IO[bytes]) -> List[str]:
    data = _decompress_zstd_file(file)
    return _extract_filenames(data)


def _decompress_zstd_file(file: IO[bytes]) -> bytes:
    result = b""
    dctx = zstandard.ZstdDecompressor()
    decompressor = dctx.stream_reader(file)
    while True:
        chunk = decompressor.read(ZSTD_CHUNK_SIZE)
        if not chunk:
            break
        result += chunk
    return result


def _extract_filenames(data: bytes) -> List[str]:
    """Extracts the filenames from the new media file format, which is a protobuf file."""
    result = MediaEntries()
    result.ParseFromString(data)
    return [entry.name for entry in result.entries]


class FileInZip(FileLike):
    name: str
    extension: str
    _name_in_zip: str
    _zip_file: zipfile.ZipFile

    def __init__(
        self,
        name: str,
        zip_path: Path,
        name_in_zip: str,
    ):
        self.name = name
        self.extension = name.split(".")[-1]
        self._zip_file: zipfile.ZipFile = zipfile.ZipFile(zip_path, "r")
        self._name_in_zip = name_in_zip

    @cached_property
    def size(self) -> int:  # type: ignore
        return self._zip_file.getinfo(self._name_in_zip).file_size

    @cached_property
    def md5(self) -> str:
       return md5(self.read_bytes()).hexdigest()

    def read_bytes(self) -> bytes:
        return self._zip_file.read(self._name_in_zip)

    def is_identical(self, file: FileLike) -> bool:
        try:
            return file.size == self.size and file.md5 == self.md5  # type: ignore
        except AttributeError:
            return file.size == self.size
