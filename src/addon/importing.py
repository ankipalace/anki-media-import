from concurrent.futures import Future
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple, NamedTuple
import unicodedata

from anki.media import media_paths_from_col_path
from aqt import mw
import aqt.editor

from .pathlike import FileLike, PathLike, LocalPath, RequestError


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

    try:
        # 1. Get the name of all media files.
        files_list = get_list_of_files(src)
        if files_list is None:
            log(f"Error - Invalid Path: {src}")
            result = ImportResult(logs, success=False)
            on_done(result)
            return
        initial_tot_cnt = len(files_list)
        log(f"{initial_tot_cnt} media files found.")

        # 2. Normalize file names
        unnormalized = find_unnormalized_name(files_list)
        if len(unnormalized):
            log(f"{len(unnormalized)} files have invalid file names: {unnormalized}")
            result = ImportResult(logs, success=False)
            on_done(result)
            return

        # 3. Make sure there isn't a name conflict within new files.
        if name_conflict_exists(files_list):
            log("There are multiple files with same filename.")
            result = ImportResult(logs, success=False)
            on_done(result)
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
            log(f"{len(name_conflicts)} files have the same name as existing media files.")
            result = ImportResult(logs, success=False)
            on_done(result)
            return
        cnt_diff = prev_cnt - tot_cnt
        if cnt_diff:
            log(f"{cnt_diff} files were skipped because they already exist in collection.")

        if tot_cnt == 0:
            log(f"{initial_tot_cnt} media files were imported")
            result = ImportResult(logs, success=True)
            on_done(result)
            return

    except RequestError as err:
        log(str(err))
        result = ImportResult(logs, success=False)
        on_done(result)
        return

    # 5. Add media files in chunk in background.
    log(f"{tot_cnt} media files will be added to collection", debug=True)
    diff = initial_tot_cnt - tot_cnt

    def add_files(fut: Future, idx: int) -> None:
        done_cnt = idx + diff
        if fut is not None:
            try:
                fut.result()  # Check if add_files raised an error
            except RequestError as err:
                log(f"{str(err)}\n{done_cnt} / {initial_tot_cnt} media files were added.")
                result = ImportResult(logs, success=False)
                on_done(result)
                return

        # Sometimes add_files is called before progress window is repainted
        mw.progress.update(
            label=f"Adding media files ({done_cnt} / {initial_tot_cnt})",
            value=done_cnt, max=initial_tot_cnt)

        # Last file was added
        if idx == tot_cnt:
            log(f"{initial_tot_cnt} media files were imported.")
            result = ImportResult(logs, success=True)
            on_done(result)
            return

        # Abort import
        if mw.progress.want_cancel():
            log(f"Import aborted.\n{done_cnt} / {initial_tot_cnt} media files were imported.")
            result = ImportResult(logs, success=False)
            on_done(result)
            return

        mw.taskman.run_in_background(
            add_media, lambda fut: add_files(fut, idx),
            args={"file": files_list[idx]})
        idx += 1

    add_files(None, 0)


def get_list_of_files(path: PathLike) -> Optional[List[FileLike]]:
    """Returns list of files in src, including in its subdirectories. 
       Returns None if src is neither file nor directory."""
    files_list: List[FileLike] = []
    if path.is_file():
        files_list.append(path.to_file())
    elif path.is_dir():
        search_files(files_list, path, recursive=True)
    else:
        return None
    return files_list


def search_files(files: List[FileLike], src: PathLike, recursive: bool) -> None:
    """Searches for files recursively, adding them to files. src must be a directory."""
    for path in src.iterdir():
        if path.is_file():
            file = path.to_file()
            if file.extension.lower() in MEDIA_EXT:  # remove '.'
                files.append(file)
        elif recursive and path.is_dir():
            search_files(files, path, recursive=True)


def find_unnormalized_name(files: List[FileLike]) -> List[FileLike]:
    """Returns list of files whose names are not normalized."""
    unnormalized = []
    for idx, file in enumerate(files):
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
            if file.md5 == file_names[name].md5:
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
    collection_file_paths: List[FileLike] = []
    media_dir = LocalPath(media_paths_from_col_path(mw.col.path)[0])
    search_files(collection_file_paths, media_dir, recursive=False)
    collection_files = {file.name: file for file in collection_file_paths}

    name_conflicts: List[FileLike] = []
    identical: List[int] = []

    for idx, file in enumerate(files_list):
        if file.name in collection_files:
            if file.md5 == collection_files[file.name].md5:
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
