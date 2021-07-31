from concurrent.futures import Future
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unicodedata
import shutil

from anki.media import media_paths_from_col_path
from anki.utils import checksum
from aqt import mw
from aqt.utils import tooltip
import aqt.editor

MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio
DEBUG_PREFIX = "Media Import:"
TEMP_DIR = Path(__file__).resolve().parent / "TEMP"


def import_media(src: Path) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    TODO: collect various import ending into one
    """

    # 1. Get the name of all media files.
    mw.progress.start(
        parent=mw, label="Starting import", immediate=True)  # type: ignore
    files_list = get_list_of_files(src)
    if files_list is None:
        mw.progress.finish()
        tooltip("Invalid Path", parent=mw)
        return
    print(f"{DEBUG_PREFIX} {len(files_list)} files found.")

    # 2. Normalize file names
    normalize_name(files_list)

    # 3. Make sure there isn't a name conflict within new files.
    if name_conflict_exists(files_list):
        msg = "There are multiple files with same name."
        mw.progress.finish()
        print(f"{DEBUG_PREFIX} {msg}")
        tooltip(msg, parent=mw)
        return

    # 4. Check collection.media if there is a file with same name.
    # TODO: Allow user to rename/overwrite file
    name_conflicts = name_exists_in_collection(files_list)
    if len(name_conflicts):
        msg = "{} files have the same name as existing media files."
        mw.progress.finish()
        print(f"{DEBUG_PREFIX} {msg}")
        tooltip(msg, parent=mw)
        return

    # 5. Add media files in chunk in background.
    CHUNK_SIZE = 5
    totcnt = len(files_list)
    print(f"{DEBUG_PREFIX} Adding media - total {totcnt} files.")

    # 6. Write output: How many added, how many not actually in notes...?
    # TODO: Better reports - identical files, etc.
    def finish_import() -> None:
        delete_temp_folder()
        mw.progress.finish()
        msg = f"{totcnt} media files added."
        print(f"{DEBUG_PREFIX} {msg}")
        tooltip(msg, parent=mw)

    def abort_import(count: int) -> None:
        delete_temp_folder()
        mw.progress.finish()
        msg = f"Aborted import. {count} / {totcnt} media files were added."
        print(f"{DEBUG_PREFIX} {msg}")
        tooltip(msg, parent=mw)

    def add_files(files: List[Path]) -> None:
        for file in files:
            add_media(file)

    def add_files_chunk(fut: Future, start: int) -> None:
        if fut is not None:
            fut.result()  # Check if add_files raised an error

        # Sometimes add_files is called before progress window is repainted
        mw.progress.update(
            label=f"Adding media files ({start} / {totcnt})", value=start, max=totcnt)

        # Last chunk was added
        if start == totcnt:
            finish_import()
            return

        if mw.progress.want_cancel():
            abort_import(start)
            return

        end = start + CHUNK_SIZE
        if end > totcnt:
            end = totcnt

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
