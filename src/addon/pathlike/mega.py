from typing import Any, Dict, List, Tuple, Union, Optional
import random
import requests
import json
import re

from Crypto.Cipher import AES
from Crypto.Util import Counter
from mega.errors import RequestError as MegaReqError
from mega.crypto import a32_to_str, base64_to_a32, base64_url_decode, decrypt_attr, decrypt_key

from .base import RootPath, FileLike
from .errors import MalformedURLError, RootNotFoundError, RequestError

"""
Mega node (file/folder) datatype:
h: str - id of the node
p: str - id of its parent node
u: str - user id
t: int[0-3] - node type. 0: file, 1: folder
a: str - encrypted dictionary of attributes 
    {n: str - name, c: str - hash? maybe based on creation time }
k: str - file key. Use shared folder's key to create the real file's key
s: int - file size
ts: int - timestamp
"""


class Mega:
    def __init__(self) -> None:
        self.sequence_num = random.randint(0, 0xFFFFFFFF)
        self.REGEXP = r"https?://mega.(?:io|nz|co\.nz)/folder/([0-z-_]+)#([0-z-_]+)"
        self.URL_PATTERN = re.compile(self.REGEXP)

    def api_request(self, data: Union[dict, list], root_folder: Optional[str]) -> dict:
        params: Dict[str, Any] = {
            "id": self.sequence_num
        }
        if root_folder:
            params["n"] = root_folder
        self.sequence_num += 1

        # ensure input data is a list
        if not isinstance(data, list):
            data = [data]

        url = r"https://g.api.mega.co.nz/cs"
        response = requests.post(
            url,
            params=params,
            data=json.dumps(data)
        )
        json_resp = json.loads(response.text)

        try:
            if isinstance(json_resp, list):
                int_resp = json_resp[0] if isinstance(json_resp[0],
                                                      int) else None
            elif isinstance(json_resp, int):
                int_resp = json_resp

        except IndexError:
            int_resp = None
        if int_resp is not None:
            raise MegaReqError(int_resp)
        return json_resp[0]

    def download_file(self, root_folder: str, file_id: str, file_key: Tuple[int, ...]) -> bytes:
        print(root_folder, file_id)
        file_data = self.api_request({
            'a': 'g',
            'g': 1,
            'n': file_id
        }, root_folder)

        k = self.xor_key(file_key)
        iv = file_key[4:6] + (0, 0)

        # Seems to happens sometime... When this occurs, files are
        # inaccessible also in the official also in the official web app.
        # Strangely, files can come back later.
        if 'g' not in file_data:
            raise MegaReqError('File not accessible anymore')
        file_url = file_data['g']
        encrypted_file = requests.get(file_url).content

        k_str = a32_to_str(k)
        counter = Counter.new(128, initial_value=((iv[0] << 32) + iv[1]) << 64)
        aes = AES.new(k_str, AES.MODE_CTR, counter=counter)
        file = aes.decrypt(encrypted_file)

        return file

    def parse_url(self, url: str) -> Optional[Tuple[str, str]]:
        "Returns (id, key) if valid. If not returns None."
        m = re.search(self.URL_PATTERN, url)
        if m:
            if url.count("/folder/") > 1:
                # TODO: subfolder of a shared folder
                raise MalformedURLError()
            return (m.group(1), m.group(2))
        raise MalformedURLError()

    def xor_key(self, key: Tuple[int, ...]) -> Tuple[int, ...]:
        return (key[0] ^ key[4], key[1] ^ key[5], key[2] ^ key[6], key[3] ^ key[7])


mega = Mega()


class MegaRoot(RootPath):
    id: str
    shared_key: str
    files: List["FileLike"]

    def __init__(self, url: str) -> None:
        (id, key) = mega.parse_url(url)
        self.id = id
        self.shared_key = base64_to_a32(key)
        self.files = self.list_files(recursive=True)

    def list_files(self, recursive: bool = True) -> List[FileLike]:
        data = [{"a": "f", "c": 1, "ca": 1, "r": 1}]
        nodes = mega.api_request(data, self.id)["f"]
        files: List[FileLike] = []
        root_id = nodes[0]["h"]
        for node in nodes:
            if node["t"] != 0:  # 1: folder, 2-3: Trash can, etc.
                continue
            if not recursive and node["p"] != root_id:
                continue
            encrypted_key = base64_to_a32(node["k"].split(":")[1])
            key = decrypt_key(encrypted_key, self.shared_key)
            k = mega.xor_key(key)
            attrs = decrypt_attr(base64_url_decode(node["a"]), k)
            name = attrs["n"]
            if not '.' in name:
                continue
            ext = name.split(".")[-1]
            if not self.has_media_ext(ext):
                continue
            file = MegaFile(root=self, id=node["h"], key=key,
                            name=attrs["n"], ext=ext, size=node["s"])
            files.append(file)
        return files


class MegaFile(FileLike):
    id: str  # A string that can identify the file
    name: str
    extension: str
    size: float

    key: Tuple[int, ...]
    root: MegaRoot

    def __init__(self, root: MegaRoot, id: str, key: Tuple[int, ...], name: str, ext: str, size: float) -> None:
        self.root = root
        self.id = id
        self.key = key
        self.name = name
        self.extension = ext
        self.size = size

    def read_bytes(self) -> bytes:
        return mega.download_file(self.root.id, self.id, self.key)

    def is_identical(self, file: FileLike) -> bool:
        return file.size == self.size
