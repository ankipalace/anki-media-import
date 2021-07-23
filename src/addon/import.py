from pathlib import Path
from typing import Dict, List, Tuple
import unicodedata

from anki.media import media_paths_from_col_path
from aqt import mw
from aqt.utils import tooltip
import aqt.editor


MEDIA_DIR = Path(media_paths_from_col_path(mw.col.path)[0])
MEDIA_EXT: Tuple[str] = aqt.editor.pics + aqt.editor.audio


def import_media(src: Path) -> None:
    """
    Import media from a directory, and its subdirectories.
    TODO: Allow importing an individual media.
    """
    assert src.is_dir()
    # 1. Get the name of all media files.
    files_list: List[Path] = []
    search_files(files_list, src)

    # 2. Normalize file names
    normalize_name(files_list)

    # 3. Make sure there isn't a naming conflict.
    duplicates = search_name_conflict(files_list)
    assert len(duplicates) == 0

    # 4. Add the media.
    for file in files_list:
        add_media(file)

    # 5. Write output: How many added, how many not actually in notes...?
    tooltip("{} media files added.".format(len(files_list)))


def search_files(files: List[Path], src: Path) -> None:
    """Searches for files recursively, adding them to files"""
    for path in src.iterdir():
        if path.is_file():
            if path.suffix in MEDIA_EXT:
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


def search_name_conflict(new_files: List[Path]) -> List[Path]:
    """
        Would be great if we could get the file names from the media.db,
        but currently not quite easy to access it unlike collection db.
        TODO: If there's a name conflict with existing file, check if they have same content.
    """
    # 1. Search for name conflicts within new media
    # Which can happen if the media are in different subdirectories
    # 2. Search for name conflicts in existing media
    existing_files: List[Path] = []
    search_files(existing_files, MEDIA_DIR)

    file_names: Dict[str, Path] = {}
    duplicate_files: Dict[str, List[Path]] = {}

    for files in (new_files, existing_files):
        for file in files:
            name = file.name
            if name not in file_names:
                file_names[name] = file
            else:  # There may be more than 2 duplicate files
                if name not in duplicate_files:
                    duplicate = file_names[name]
                    duplicate_files[name] = [duplicate]
                duplicate_files[name].append(file)
    return duplicate_files


def add_media(src: Path) -> None:
    """
        Tries to add media with the same basename.
        But may change the name if it overlaps with existing media.
        Therefore make sure there isn't an existing media with the same name!
    """
    mw.col.media.add_file(src)
