from concurrent.futures import Future
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import unicodedata

from anki.media import media_paths_from_col_path
from anki.utils import checksum
from aqt import mw
from aqt.utils import tooltip
from aqt.qt import QApplication
import aqt.editor

MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio
DEBUG_PREFIX = "Media Import:"


def import_media(src: Path) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    This may rename original files to remove invalid characters from file names.
    """

    # 1. Get the name of all media files.
    mw.progress.start(
        parent=mw, label="Starting import", immediate=True)
    files_list = get_list_of_files(src)
    if files_list is None:
        tooltip("Invalid Path")
        return

    # 2. Normalize file names
    normalize_name(files_list)

    # 3. Make sure there isn't a naming conflict.
    name_conflicts = search_name_conflict(files_list)
    filter_duplicate_files(name_conflicts)
    assert len(name_conflicts) == 0

    # 4. Add media files in chunk in background.
    CHUNK_SIZE = 20
    totcnt = len(files_list)
    print("Media Import: Adding media")

    # 5. Write output: How many added, how many not actually in notes...? (on_done)
    def finish_import() -> None:
        mw.progress.finish()
        print(f"{DEBUG_PREFIX} {totcnt} Media Files added")
        tooltip(f"{totcnt} media files added.")

    def add_files(files: List[Path]) -> None:
        for file in files:
            add_media(file)

    # TODO: allow canceling mid-import.
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
        search_files(files_list, src)
    else:
        print(f"{DEBUG_PREFIX} Invalid path: {src}")
        return None
    return files_list


def search_files(files: List[Path], src: Path) -> None:
    """Searches for files recursively, adding them to files. src must be a directory."""
    for path in src.iterdir():
        if path.is_file():
            if path.suffix[1:] in MEDIA_EXT:  # remove '.'
                files.append(path)
        elif path.is_dir():
            search_files(files, path)


def normalize_name(files: List[Path]) -> None:
    """Renames media files to have normalized names."""
    for file in files:
        name = file.name
        normalized_name = unicodedata.normalize("NFC", name)
        if name != normalized_name:
            file.rename(normalized_name)


def search_name_conflict(new_files: List[Path]) -> Dict[str, List[Path]]:
    """
        Would be great if we could get the file names from the media.db,
        but currently not quite easy to access it unlike collection db.
    """
    # 1. Search for name conflicts within new media
    # Which can happen if the media are in different subdirectories
    # 2. Search for name conflicts in existing media
    existing_files: List[Path] = []
    media_dir = Path(media_paths_from_col_path(mw.col.path)[0])
    search_files(existing_files, media_dir)

    file_names: Dict[str, Path] = {}
    name_conflicts: Dict[str, List[Path]] = {}

    for files in (new_files, existing_files):
        for file in files:
            name = file.name
            if name not in file_names:
                file_names[name] = file
            else:  # There may be more than 2 duplicate files
                if name not in name_conflicts:
                    duplicate = file_names[name]
                    name_conflicts[name] = [duplicate]
                name_conflicts[name].append(file)

    return name_conflicts


def hash_file(file: Path) -> str:
    return checksum(file.read_bytes())


def is_duplicate_file(files: List[Path]) -> bool:
    assert len(files) > 1
    file_checksum = hash_file(files[0])
    for i in range(1, len(files)):
        file = files[i]
        if hash_file(file) != file_checksum:
            return False
    return True


def filter_duplicate_files(name_conflicts: Dict[str, List[Path]]) -> None:
    """Removes files whose content is identical from name_conflicts """
    for file_name in list(name_conflicts.keys()):
        files = name_conflicts[file_name]
        if is_duplicate_file(files):
            del name_conflicts[file_name]


def add_media(src: Path) -> None:
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    new_name = mw.col.media.add_file(str(src))
    assert new_name == src.name
