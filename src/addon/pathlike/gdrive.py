from typing import List
import os
import requests


from .base import FileLike, RootPath

# TODO: Handle network errors, api errors, invalid id, etc.
# TODO: (don't) handle google docs file
# TODO: package api key into the addon

API_KEY = os.environ['GOOGLE_DRIVE_API_KEY']


class RequestError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__()
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"RequestError<{self.code}>: {self.msg}"


class GDrive():
    BASE_URL = "https://www.googleapis.com/drive/v3/files"
    FIELDS_STR = ','.join(["id", "name", "md5Checksum",
                           "mimeType", "fileExtension", "size"])

    def get_metadata(self, id: str) -> dict:
        url = f"{self.BASE_URL}/{id}"
        return self.make_request(url, params={
            "fields": self.FIELDS_STR,
            "key": API_KEY
        }).json()

    def list_paths(self, id: str) -> dict:
        url = self.BASE_URL
        return self.make_request(url, params={
            "q": f"'{id}' in parents",
            "fields": "files({})".format(self.FIELDS_STR),
            "key": API_KEY
        }).json()

    def download_file(self, id: str) -> bytes:
        url = f"{self.BASE_URL}/{id}"
        res = self.make_request(url, params={
            "alt": "media",
            "key": API_KEY
        })
        return res.content

    def make_request(self, url: str, params: dict) -> requests.Response:
        res = requests.get(url, params)
        if res.ok:
            return res

        # Error occured!
        body = res.json()["error"]
        code = body["code"]
        errors = body["errors"]
        if errors:
            message = "".join([err["message"] for err in errors])
        else:
            message = body["message"]
        raise RequestError(code, message)

    def is_folder(self, pathdata: dict) -> bool:
        return pathdata["mimeType"] == "application/vnd.google-apps.folder"


gdrive = GDrive()


class GDriveRoot(RootPath):
    id: str

    def __init__(self, data: dict = {}, id: str = "") -> None:
        if not data:
            if not id:
                raise ValueError(
                    "Either data or id should be passed when initializing GDrivePath.")
            data = gdrive.get_metadata(id)
        self.id = data["id"]

    def list_files(self, recursive: bool) -> List["FileLike"]:
        files: List["FileLike"] = []
        self.search_files(files, self.id, recursive)
        return files

    def search_files(self, files: List["FileLike"], id: str, recursive: bool) -> None:
        # TODO: only list files with appropriate mime type
        res = gdrive.list_paths(id)
        paths = res["files"]
        for path in paths:
            if gdrive.is_folder(path):
                if recursive:
                    self.search_files(files, path["id"], recursive=True)
            elif self.is_media_ext(path["extension"]):
                file = GDriveFile(path)
                files.append(file)


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
        self._md5 = data["md5Checksum"]

    def read_bytes(self) -> bytes:
        return gdrive.download_file(self.id)

    @property
    def md5(self) -> str:
        return self._md5

    def is_identical(self, file: "FileLike") -> bool:
        try:  # Calculating md5 is slow for local file.
            return file.size == self.size and file.md5 == self.md5  # type: ignore
        except AttributeError:
            return file.size == self.size
