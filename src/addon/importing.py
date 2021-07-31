from concurrent.futures import Future
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple, NamedTuple
import unicodedata
import shutil

from anki.media import media_paths_from_col_path
from anki.utils import checksum
from aqt import mw
import aqt.editor


MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio
TEMP_DIR = Path(__file__).resolve().parent / "TEMP"


class ImportResult(NamedTuple):
    logs: List[str]
    msg: str
    success: bool


def import_media(src: Path, on_done: Callable[[ImportResult], None]) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    TODO: collect various import ending into one
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
        result = ImportResult(logs, "Error - Invalid Path", success=False)
        on_done(result)
        return
    tot_cnt = len(files_list)
    log(f"{tot_cnt} media files found.")

    # 2. Normalize file names
    normalize_name(files_list)

    # 3. Make sure there isn't a name conflict within new files.
    prev_cnt = tot_cnt
    if name_conflict_exists(files_list):
        log("There are multiple files with same filename.")
        result = ImportResult(
            logs, "Error - Filename conflict", success=False)
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
        result = ImportResult(
            logs, "Error - Filename Conflict", success=False)
        on_done(result)
        return
    cnt_diff = prev_cnt - tot_cnt
    if cnt_diff:
        log(f"{cnt_diff} files were skipped because they already exist in collection.")

    # 5. Add media files in chunk in background.
    CHUNK_SIZE = 5
    log(f"{tot_cnt} media files will be added to collection", debug=True)

    def add_files(files: List[Path]) -> None:
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
            result = ImportResult(
                logs, f"Imported {tot_cnt} Media Files", success=True)
            on_done(result)
            return

        # Abort import
        if mw.progress.want_cancel():
            log(f"Aborted import. {start} / {tot_cnt} media files were imported.")
            result = ImportResult(logs, "Import Aborted", success=False)
            on_done(result)
            return

        end = start + CHUNK_SIZE
        if end > tot_cnt:
            end = tot_cnt

        mw.taskman.run_in_background(
            add_files, lambda fut: add_files_chunk(fut, end),
            args={"files": files_list[start:end]})

    add_files_chunk(None, 0)


def get_list_of_files(src: Path) -> Optional[List[Path]]:
    """Returns list of files in src, including in its subdirectories. 
       Returns None if src is neither file nor directory."""
    files_list: List[Path] = []
    if src.is_file():
        files_list.append(src)
    elif src.is_dir():
        search_files(files_list, src, recursive=True)
    else:
        return None
    return files_list


def search_files(files: List[Path], src: Path, recursive: bool) -> None:
    """Searches for files recursively, adding them to files. src must be a directory."""
    for path in src.iterdir():
        if path.is_file():
            if path.suffix[1:].lower() in MEDIA_EXT:  # remove '.'
                files.append(path)
        elif recursive and path.is_dir():
            search_files(files, path, recursive=True)


def normalize_name(files: List[Path]) -> None:
    """If file name is not normalized, copy the file to a temp dir and rename it."""
    TEMP_DIR.mkdir(exist_ok=True)

    for idx, file in enumerate(files):
        name = file.name
        normalized_name = unicodedata.normalize("NFC", name)
        if name != normalized_name:
            new_file = TEMP_DIR / normalized_name
            shutil.copy(str(file), str(new_file))
            files[idx] = new_file


def delete_temp_folder() -> None:
    if TEMP_DIR.is_dir():
        shutil.rmtree(str(TEMP_DIR))


def hash_file(file: Path) -> str:
    return checksum(file.read_bytes())


def name_conflict_exists(files_list: List[Path]) -> bool:
    """Returns True if there are different files with the same name.
       And removes identical files from files_list so only one remains. """
    file_names: Dict[str, Path] = {}  # {file_name: file_path}
    for file in files_list:
        name = file.name
        if name in file_names:
            if hash_file(file) == hash_file(file_names[name]):
                files_list.remove(file)
            else:
                return True
        else:
            file_names[name] = file
    return False


def name_exists_in_collection(files_list: List[Path]) -> List[Path]:
    """Returns list of files whose names conflict with existing media files.
       And remove files if identical file exists in collection. """
    collection_files: List[Path] = []
    media_dir = Path(media_paths_from_col_path(mw.col.path)[0]).resolve()
    search_files(collection_files, media_dir, recursive=False)
    collection_file_names = [file.name for file in collection_files]

    name_conflicts: List[Path] = []

    for file in files_list:
        if file.name in collection_file_names:
            if hash_file(file) == hash_file(media_dir / file.name):
                files_list.remove(file)
            else:
                name_conflicts.append(file)

    return name_conflicts


def add_media(src: Path) -> None:
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    new_name = mw.col.media.add_file(str(src))
    assert new_name == src.name
