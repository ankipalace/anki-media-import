from concurrent.futures import Future
from typing import Callable, Dict, List, NamedTuple, Sequence, NamedTuple
import unicodedata

from anki.media import media_paths_from_col_path
from aqt import mw

from .pathlike import FileLike, RootPath, LocalRoot, RequestError


class ImportResult(NamedTuple):
    logs: List[str]
    success: bool


def import_media(src: RootPath, on_done: Callable[[ImportResult], None]) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    TODO: import_media MUST call finish_import even when exception occurs
    """

    logs: List[str] = []

    def log(msg: str) -> None:
        print(f"Media Import: {msg}")
        logs.append(msg)

    def finish_import(msg: str, success: bool) -> None:
        log(msg)
        result = ImportResult(logs, success)
        on_done(result)

    try:
        # 1. Get the name of all media files.
        files_list = src.list_files(recursive=True)
        initial_tot_cnt = len(files_list)
        log(f"{initial_tot_cnt} media files found.")

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
        tot_cnt = len(files_list)
        cnt_diff = initial_tot_cnt - tot_cnt
        if cnt_diff:
            log(f"{cnt_diff} files were skipped because they are identical.")

        # 4. Check collection.media if there is a file with same name.
        # TODO: Allow user to rename/overwrite file
        prev_cnt = tot_cnt
        name_conflicts = name_exists_in_collection(files_list)
        tot_cnt = len(files_list)
        if len(name_conflicts):
            finish_import(f"{len(name_conflicts)} files have the same name as existing media files.",
                          success=False)
            return
        cnt_diff = prev_cnt - tot_cnt
        if cnt_diff:
            log(f"{cnt_diff} files were skipped because they already exist in collection.")

        if tot_cnt == 0:
            finish_import(
                f"{initial_tot_cnt} media files were imported", success=True)
            return

    except RequestError as err:
        finish_import(str(err), success=False)
        return

    # 5. Add media files in chunk in background.
    log(f"{tot_cnt} media files will be processed.")
    diff = initial_tot_cnt - tot_cnt

    def add_files(fut: Future, idx: int) -> None:
        done_cnt = idx + diff
        if fut is not None:
            try:
                fut.result()  # Check if add_files raised an error
            except RequestError as err:
                finish_import(f"{str(err)}\n{done_cnt} / {initial_tot_cnt} media files were added.",
                              success=False)
                return

        # Sometimes add_files is called before progress window is repainted
        mw.progress.update(
            label=f"Adding media files ({done_cnt} / {initial_tot_cnt})",
            value=done_cnt, max=initial_tot_cnt)

        # Last file was added
        if idx == tot_cnt:
            finish_import(
                f"{initial_tot_cnt} media files were imported.", success=True)
            return

        # Abort import
        if mw.progress.want_cancel():
            finish_import(f"Import aborted.\n{done_cnt} / {initial_tot_cnt} media files were imported.",
                          success=False)
            return

        mw.taskman.run_in_background(
            add_media, lambda fut: add_files(fut, idx),
            args={"file": files_list[idx]})
        idx += 1

    add_files(None, 0)


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
    media_dir = LocalRoot(media_paths_from_col_path(mw.col.path)[0])
    collection_file_paths = media_dir.list_files(recursive=False)
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


def add_media(file: FileLike) -> None:  # TODO: gdrive
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    new_name = mw.col.media.write_data(file.name, file.read_bytes())
    assert new_name == file.name  # TODO: write an error dialogue?
