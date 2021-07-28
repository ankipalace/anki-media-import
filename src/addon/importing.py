from pathlib import Path
from typing import Dict, List, Tuple
import unicodedata

from anki.media import media_paths_from_col_path
from anki.utils import checksum
from aqt import mw
from aqt.utils import tooltip
import aqt.editor

MEDIA_EXT: Tuple[str, ...] = aqt.editor.pics + aqt.editor.audio
DEBUG_PREFIX = "Media Import:"


def import_media(src: Path) -> None:
    """
    Import media from a directory, and its subdirectories. 
    (Or import a specific file.)
    """

    # 1. Get the name of all media files.
    files_list: List[Path] = []
    if src.is_file():
        files_list.append(src)
    elif src.is_dir():
        search_files(files_list, src)
    else:
        print(f"{DEBUG_PREFIX} Invalid path: {src}")
        return
    print(f"{DEBUG_PREFIX} {len(files_list)} Media Files Found")

    # 2. Normalize file names
    normalize_name(files_list)

    # 3. Make sure there isn't a naming conflict.
    name_conflicts = search_name_conflict(files_list)
    filter_duplicate_files(name_conflicts)
    assert len(name_conflicts) == 0

    # 4. Add the media.
    for file in files_list:
        add_media(file)

    # 5. Write output: How many added, how many not actually in notes...?
    tooltip("{} media files added.".format(len(files_list)))
    print(f"{DEBUG_PREFIX} import done: {len(files_list)} files")


def search_files(files: List[Path], src: Path) -> None:
    """Searches for files recursively, adding them to files"""
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
        TODO: If there's a name conflict with existing file, check if they have same content.
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
    for file_name in name_conflicts:
        files = name_conflicts[file_name]
        if is_duplicate_file(files):
            del name_conflicts[file_name]


def add_media(src: Path) -> None:
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    mw.col.media.add_file(str(src))
