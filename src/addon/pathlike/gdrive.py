from typing import TypedDict, List
import os
import requests
from datetime import datetime

from .base import PathLike

API_KEY = os.environ['GOOGLE_DRIVE_API_KEY']


class GDrivePath(PathLike):
    id: str
    name: str
    md5: str
    mimeType: str
    fileExtension: str
    modifiedTime: datetime
    size: float

    fields = ["id", "name", "md5", "mimeType",
              "fileExtension", "modifiedTime", "size"]

    def __init__(self, data: dict) -> None:
        for field in self.fields:
            setattr(self, field, data[field])

    def is_file(self) -> bool:
        return not self.is_dir()

    def is_dir(self) -> bool:
        return self.mimeType == "application/vnd.google-apps.folder"

    def iterdir(self) -> List["GDrivePath"]:
        url = "https://www.googleapis.com/drive/v3/files"
        res = requests.get(url, params={
            "q": f"'{id}' in parents",
            "fields": self.fields,
            "key": API_KEY
        }).json()
        files = res["items"]
        return [GDrivePath(file) for file in files]

    @property
    def data(self) -> bytes:
        url = f"https://www.googleapis.com/drive/v3/files/{self.id}"
        res = requests.get(url, params={
            "alt": "media",
            "key": API_KEY
        })
        # TODO: unzip data and ...
        return bytes(1)

    @property
    def extension(self) -> str:
        return self.fileExtension
