from typing import List
import os
import requests

from .base import FileLike, PathLike

# TODO: Handle network errors, api errors, invalid id, etc.


API_KEY = os.environ['GOOGLE_DRIVE_API_KEY']
FIELDS = ["id", "name", "md5Checksum", "mimeType",
          "fileExtension", "size"]


def get_metadata(id: str) -> dict:
    url = f"https://www.googleapis.com/drive/v3/files/{id}"
    print(f"getting metadata from {url}")
    res = requests.get(url, params={
        "fields": ",".join(FIELDS),
        "key": API_KEY
    }).json()
    return res


class GDrivePath(PathLike):
    _data: dict
    _id: str
    _is_dir: bool

    def __init__(self, data: dict = {}, id: str = "") -> None:
        if not data:
            if not id:
                raise ValueError(
                    "Either data or id should be passed when initializing GDrivePath.")
            data = get_metadata(id)
        self._data = data
        self._id = data["id"]
        if data["_mimeType"] == "application/vnd.google-apps.folder":
            self._is_dir = True

    def is_file(self) -> bool:
        return not self._is_dir

    def is_dir(self) -> bool:
        return self._is_dir

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

    def to_file(self) -> "GDriveFile":
        return GDriveFile(self._data)


class GDriveFile(FileLike):
    key: str  # == id
    name: str
    extension: str
    size: float

    _md5: str
    id: str

    def __init__(self, data: dict) -> None:
        if not data:
            raise ValueError(
                "Either data or id should be passed when initializing GDrivePath.")
        self.path = data["id"]
        self.name = data["name"]
        self.extension = data["fileExtension"]
        self.size = data["size"]
        self.id = self.path
        self._md5 = data["md5"]

    def read_bytes(self) -> bytes:
        url = f"https://www.googleapis.com/drive/v3/files/{self.id}"
        res = requests.get(url, params={
            "alt": "media",
            "key": API_KEY
        })
        return res.content

    @property
    def md5(self) -> str:
        return self._md5
