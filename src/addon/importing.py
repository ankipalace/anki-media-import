from concurrent.futures import Future
from typing import Callable, Dict, List, NamedTuple, Sequence, NamedTuple, Optional
from requests.exceptions import RequestException
import unicodedata

from anki.media import media_paths_from_col_path
from aqt import mw

from .pathlike import FileLike, RootPath, LocalRoot
from .pathlike.errors import AddonError


class ImportResult(NamedTuple):
    logs: List[str]
    success: bool


class FilesCount():
    files: list
    tot: int
    prev: int

    def __init__(self, files: list) -> None:
        self.files = files
        self.tot = len(files)
        self.prev = self.tot
        self.diff = 0

    def update_diff(self) -> int:
        """ Returns `curr - prev`, then updates prev to curr """
        self.diff = self.prev - self.curr
        self.prev = self.curr
        return self.diff

    @property
    def curr(self) -> int:
        return len(self.files)

    @property
    def left(self) -> int:
        return self.tot - self.curr


def import_media(src: RootPath, on_done: Callable[[ImportResult], None]) -> None:
    """
    Import media from a directory, and its subdirectories. 
    """
    logs: List[str] = []

    try:
        _import_media(logs, src, on_done)
    except Exception as err:
        print(str(err))
        logs.append(str(err))
        res = ImportResult(logs, success=False)
        on_done(res)


def _import_media(logs: List[str], src: RootPath, on_done: Callable[[ImportResult], None]) -> None:

    def log(msg: str) -> None:
        print(f"Media Import: {msg}")
        logs.append(msg)

    def finish_import(msg: str, success: bool) -> None:
        log(msg)
        result = ImportResult(logs, success)
        on_done(result)

    # 1. Get the name of all media files.
    files_list = src.files
    files_cnt = FilesCount(files_list)
    log(f"{files_cnt.tot} media files found.")

    # 2. Normalize file names
    unnormalized = find_unnormalized_name(files_list)
    if len(unnormalized):
        finish_import(f"{len(unnormalized)} files have invalid file names: {unnormalized}",
                      success=False)
        return

    # 3. Make sure there isn't a name conflict within new files.
    if name_conflict_exists(files_list):
        finish_import("There are multiple files with same filename.",
                      success=False)
        return

    if files_cnt.update_diff():
        log(f"{files_cnt.diff} files were skipped because they are identical.")

    # 4. Check collection.media if there is a file with same name.
    # TODO: Allow user to rename/overwrite file
    name_conflicts = name_exists_in_collection(files_list)
    if len(name_conflicts):
        finish_import(f"{len(name_conflicts)} files have the same name as existing media files.",
                      success=False)
        return
    if files_cnt.update_diff():
        log(f"{files_cnt.diff} files were skipped because they already exist in collection.")

    if files_cnt.curr == 0:
        finish_import(
            f"{files_cnt.tot} media files were imported", success=True)
        return

    # 5. Add media files in chunk in background.
    log(f"{files_cnt.curr} media files will be processed.")
    MAX_ERRORS = 5
    error_cnt = 0  # Count of errors in succession

    def add_next_file(fut: Optional[Future], file: Optional[FileLike]) -> None:
        nonlocal error_cnt
        if fut is not None:
            try:
                fut.result()  # Check if add_media raised an error
                error_cnt = 0
            except (AddonError, RequestException) as err:
                error_cnt += 1
                log("-"*12 + "\n" + str(err) + "\n" + "-"*12)
                if error_cnt < MAX_ERRORS:
                    if files_cnt.left < 10:
                        log(f"{files_cnt.left} files were not imported.")
                        for file in files_list:
                            log(file.name)
                    finish_import(f"{files_cnt.left} / {files_cnt.tot} media files were added.",
                                  success=False)
                    return
                else:
                    files_list.append(file)

        mw.progress.update(
            label=f"Adding media files ({files_cnt.left} / {files_cnt.tot})",
            value=files_cnt.left, max=files_cnt.tot)

        # Last file was added
        if len(files_list) == 0:
            finish_import(f"{files_cnt.tot} media files were imported.",
                          success=True)
            return

        # Abort import
        if mw.progress.want_cancel():
            finish_import(f"Import aborted.\n{files_cnt.left} / {files_cnt.tot} media files were imported.",
                          success=False)
            return
        file = files_list.pop(0)
        mw.taskman.run_in_background(
            add_media, lambda fut: add_next_file(fut, file),
            args={"file": file})

    add_next_file(None, None)


def find_unnormalized_name(files: Sequence[FileLike]) -> List[FileLike]:
    """Returns list of files whose names are not normalized."""
    unnormalized = []
    for file in files:
        name = file.name
        normalized_name = unicodedata.normalize("NFC", name)
        if name != normalized_name:
            unnormalized.append(file)
    return unnormalized


def name_conflict_exists(files_list: List[FileLike]) -> bool:
    """Returns True if there are different files with the same name.
       And removes identical files from files_list so only one remains. """
    file_names: Dict[str, FileLike] = {}  # {file_name: file_path}
    identical: List[int] = []

    for idx, file in enumerate(files_list):
        name = file.name
        if name in file_names:
            if file.is_identical(file_names[name]):
                identical.append(idx)
            else:
                return True
        else:
            file_names[name] = file
    for idx in sorted(identical, reverse=True):
        files_list.pop(idx)
    return False


def name_exists_in_collection(files_list: List[FileLike]) -> List[FileLike]:
    """Returns list of files whose names conflict with existing media files.
       And remove files if identical file exists in collection. """
    media_dir = LocalRoot(media_paths_from_col_path(
        mw.col.path)[0], recursive=False)
    collection_file_paths = media_dir.files
    collection_files = {file.name: file for file in collection_file_paths}

    name_conflicts: List[FileLike] = []
    identical: List[int] = []

    for idx, file in enumerate(files_list):
        if file.name in collection_files:
            if file.is_identical(collection_files[file.name]):
                identical.append(idx)
            else:
                name_conflicts.append(file)
    for idx in sorted(identical, reverse=True):
        files_list.pop(idx)
    return name_conflicts


def add_media(file: FileLike) -> None:
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    new_name = mw.col.media.write_data(file.name, file.read_bytes())
    assert new_name == file.name  # TODO: write an error dialogue?
