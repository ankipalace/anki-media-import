from pathlib import Path
from typing import Protocol

import aqt
import pytest
from pytest_anki import AnkiSession
from pytestqt.qtbot import QtBot  # type: ignore

from src.media_import.pathlike.base import RootPath

TEST_DATA_PATH = Path(__file__).parent / "test_data"
TEST_LOCAL_DIR = TEST_DATA_PATH / "local_directory"
TEST_OLD_APKG_PATH = TEST_DATA_PATH / "old_format.apkg"
TEST_NEW_APKG_PATH = TEST_DATA_PATH / "new_format.apkg"

class ImportTester(Protocol):
    def __call__(self, root: RootPath) -> None:
        ...

@pytest.fixture
def test_import(qtbot: QtBot) -> ImportTester:
    def _test_import(root: RootPath) -> None: # type: ignore
        from src.media_import.importing import ImportResult, import_media

        on_done_was_called = False


        def on_done(result: ImportResult) -> None:
            nonlocal on_done_was_called
            on_done_was_called = True

            assert result.success

            media_dir = Path(aqt.mw.col.media.dir())
            assert set(get_filenames_in_collection(media_dir)) == set(
                ["test1.png", "test2.png", "test3.jpg"]
            )

        import_media(root, on_done=on_done)

        qtbot.wait_until(lambda: on_done_was_called, timeout=8000)

        assert on_done_was_called
    
    return _test_import


def test_local_import(anki_session: AnkiSession, test_import: ImportTester) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.local import LocalRoot

        root = LocalRoot(TEST_LOCAL_DIR)
        test_import(root)


def test_old_apkg_import(anki_session: AnkiSession, test_import: ImportTester) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.apkg import ApkgRoot

        root = ApkgRoot(TEST_OLD_APKG_PATH)
        test_import(root)


def test_new_apkg_import(anki_session: AnkiSession, test_import: ImportTester) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.apkg import ApkgRoot
        from src.media_import.pathlike.errors import \
            IncompatibleApkgFormatError

        try:
            ApkgRoot(TEST_NEW_APKG_PATH)
        except IncompatibleApkgFormatError:
            pass
        else:
            raise AssertionError("Expected IncompatibleApkgFormatError")


def test_gdrive_import(anki_session: AnkiSession, test_import: ImportTester) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.gdrive import GDriveRoot

        root = GDriveRoot(
            "https://drive.google.com/drive/folders/1goqb4kHJHhxw4NASSd4vXMp6h04bansc"
        )
        test_import(root)


def test_mega_import(anki_session: AnkiSession, test_import: ImportTester) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.mega import MegaRoot

        root = MegaRoot("https://mega.nz/folder/HzgAAZbI#ntmzJkB4N_2N0BXdzVUvXA")
        test_import(root)



def get_filenames_in_collection(media_dir: Path) -> list[str]:
    return [x.name for x in media_dir.glob("*")]
