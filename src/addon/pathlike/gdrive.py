from typing import List
from datetime import datetime
import os
import requests

from .base import PathLike

# TODO: Handle network errors, api errors, invalid id, etc.


API_KEY = os.environ['GOOGLE_DRIVE_API_KEY']
FIELDS = ["id", "name", "md5Checksum", "mimeType",
          "fileExtension", "modifiedTime", "size"]


def get_metadata(id: str) -> dict:
    url = f"https://www.googleapis.com/drive/v3/files/{id}"
    print(f"getting metadata from {url}")
    res = requests.get(url, params={
        "fields": ",".join(FIELDS),
        "key": API_KEY
    }).json()
    return res


class GDrivePath(PathLike):
    _id: str
    _name: str
    _md5Checksum: str  # TODO: non-binary and folders don't have md5
    _mimeType: str
    _fileExtension: str
    _modifiedTime: datetime
    _size: float

    def __init__(self, data: dict = {}, id: str = "") -> None:
        if not data:
            if not id:
                raise ValueError(
                    "Either data or id should be passed when initializing GDrivePath.")
            data = get_metadata(id)
        print(data)
        for field in FIELDS:
            if field in data:
                setattr(self, f"_{field}", data[field])

    def is_file(self) -> bool:
        return not self.is_dir()

    def is_dir(self) -> bool:
        return self._mimeType == "application/vnd.google-apps.folder"

    def iterdir(self) -> List["GDrivePath"]:
        url = "https://www.googleapis.com/drive/v3/files"
        res = requests.get(url, params={
            "q": f"'{self._id}' in parents",
            "fields": "files({})".format(','.join(FIELDS)),
            "key": API_KEY
        }).json()
        print(res)
        files = res["files"]
        return [GDrivePath(data=file) for file in files]

    @property
    def name(self) -> str:
        return self._name

    @property
    def data(self) -> bytes:
        url = f"https://www.googleapis.com/drive/v3/files/{self._id}"
        res = requests.get(url, params={
            "alt": "media",
            "key": API_KEY
        })
        return res.content

    @property
    def extension(self) -> str:
        return self._fileExtension

    @property
    def md5(self) -> str:
        return self._md5Checksum
