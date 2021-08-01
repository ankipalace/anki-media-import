from concurrent.futures import Future
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple, NamedTuple
import unicodedata

from anki.media import media_paths_from_col_path
from aqt import mw
import aqt.editor

from .pathlike import PathLike, LocalPath


MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio


class ImportResult(NamedTuple):
    logs: List[str]
    success: bool


def import_media(src: PathLike, on_done: Callable[[ImportResult], None]) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    """

    logs: List[str] = []

    def log(msg: str, debug: bool = False) -> None:
        print(f"Media Import: {msg}")
        if not debug:
            logs.append(msg)

    # 1. Get the name of all media files.
    files_list = get_list_of_files(src)
    if files_list is None:
        log(f"Error - Invalid Path: {src}")
        result = ImportResult(logs, success=False)
        on_done(result)
        return
    tot_cnt = len(files_list)
    log(f"{tot_cnt} media files found.")

    # 2. Normalize file names
    unnormalized = find_unnormalized_name(files_list)
    if len(unnormalized):
        log(f"{len(unnormalized)} files have invalid file names: {unnormalized}")
        result = ImportResult(logs, success=False)
        on_done(result)
        return

        # 3. Make sure there isn't a name conflict within new files.
    prev_cnt = tot_cnt
    if name_conflict_exists(files_list):
        log("There are multiple files with same filename.")
        result = ImportResult(logs, success=False)
        on_done(result)
        return
    tot_cnt = len(files_list)
    cnt_diff = prev_cnt - tot_cnt
    if cnt_diff:
        log(f"{cnt_diff} files were skipped because they are identical.")

    # 4. Check collection.media if there is a file with same name.
    # TODO: Allow user to rename/overwrite file
    prev_cnt = tot_cnt
    name_conflicts = name_exists_in_collection(files_list)
    tot_cnt = len(files_list)
    if len(name_conflicts):
        log(f"{len(name_conflicts)} files have the same name as existing media files.")
        result = ImportResult(logs, success=False)
        on_done(result)
        return
    cnt_diff = prev_cnt - tot_cnt
    if cnt_diff:
        log(f"{cnt_diff} files were skipped because they already exist in collection.")

    # 5. Add media files in chunk in background.
    CHUNK_SIZE = 5
    log(f"{tot_cnt} media files will be added to collection", debug=True)

    def add_files(files: List[PathLike]) -> None:
        for file in files:
            add_media(file)

    def add_files_chunk(fut: Future, start: int) -> None:
        if fut is not None:
            fut.result()  # Check if add_files raised an error

        # Sometimes add_files is called before progress window is repainted
        mw.progress.update(
            label=f"Adding media files ({start} / {tot_cnt})", value=start, max=tot_cnt)

        # Last chunk was added
        if start == tot_cnt:
            log(f"{tot_cnt} media files were imported.")
            result = ImportResult(logs, success=True)
            on_done(result)
            return

        # Abort import
        if mw.progress.want_cancel():
            log(f"Import aborted. {start} / {tot_cnt} media files were imported.")
            result = ImportResult(logs, success=False)
            on_done(result)
            return

        end = start + CHUNK_SIZE
        if end > tot_cnt:
            end = tot_cnt

        mw.taskman.run_in_background(
            add_files, lambda fut: add_files_chunk(fut, end),
            args={"files": files_list[start:end]})

    add_files_chunk(None, 0)


def get_list_of_files(src: PathLike) -> Optional[List[PathLike]]:
    """Returns list of files in src, including in its subdirectories. 
       Returns None if src is neither file nor directory."""
    files_list: List[PathLike] = []
    if src.is_file():
        files_list.append(src)
    elif src.is_dir():
        search_files(files_list, src, recursive=True)
    else:
        return None
    return files_list


def search_files(files: List[PathLike], src: PathLike, recursive: bool) -> None:
    """Searches for files recursively, adding them to files. src must be a directory."""
    for path in src.iterdir():
        if path.is_file():
            if path.extension.lower() in MEDIA_EXT:  # remove '.'
                files.append(path)
        elif recursive and path.is_dir():
            search_files(files, path, recursive=True)


def find_unnormalized_name(files: List[PathLike]) -> List[PathLike]:
    """Returns list of files whose names are not normalized."""
    unnormalized = []
    for idx, file in enumerate(files):
        name = file.name
        normalized_name = unicodedata.normalize("NFC", name)
        if name != normalized_name:
            unnormalized.append(file)
    return unnormalized


def name_conflict_exists(files_list: List[PathLike]) -> bool:
    """Returns True if there are different files with the same name.
       And removes identical files from files_list so only one remains. """
    file_names: Dict[str, PathLike] = {}  # {file_name: file_path}
    for file in files_list:
        name = file.name
        if name in file_names:
            if file.md5 == file_names[name].md5:
                files_list.remove(file)
            else:
                return True
        else:
            file_names[name] = file
    return False


def name_exists_in_collection(files_list: List[PathLike]) -> List[PathLike]:
    """Returns list of files whose names conflict with existing media files.
       And remove files if identical file exists in collection. """
    collection_file_paths: List[PathLike] = []
    media_dir = LocalPath(media_paths_from_col_path(mw.col.path)[0])
    search_files(collection_file_paths, media_dir, recursive=False)
    collection_files = {file.name: file for file in collection_file_paths}

    name_conflicts: List[PathLike] = []

    for file in files_list:
        if file.name in collection_files:
            if file.md5 == collection_files[file.name].md5:
                files_list.remove(file)
            else:
                name_conflicts.append(file)

    return name_conflicts


def add_media(src: PathLike) -> None:  # TODO: gdrive
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    new_name = mw.col.media.write_data(src.name, src.data)
    assert new_name == src.name  # TODO: write an error dialogue?
