from pathlib import Path

from anki.collection import Collection
from aqt import AnkiQt
from aqt.taskman import TaskManager
from pytest_anki import AnkiSession

TEST_DATA_DIR = Path(__file__).parent / "test_data/local_directory"


def test_local_import(anki_session: AnkiSession) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.local import LocalRoot

        root = LocalRoot(TEST_DATA_DIR)
        mw = anki_session.mw
        _test_import(root, mw)


def test_gdrive_import(anki_session: AnkiSession) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.gdrive import GDriveRoot

        root = GDriveRoot(
            "https://drive.google.com/drive/folders/1goqb4kHJHhxw4NASSd4vXMp6h04bansc"
        )
        mw = anki_session.mw
        _test_import(root, mw)


def test_gdrive_as_folder_import(anki_session: AnkiSession, monkeypatch) -> None:
    # does not work yet, the js here:
    # https://github.com/ankipalace/anki-media-import/blob/7bf9cfb1d99da9eed3654ee8586e4a3cad0fa899/src/media_import/pathlike/gdrive.py#L176
    # is never executed

    with anki_session.profile_loaded():
        from src.media_import.pathlike.gdrive import GDriveRoot

        monkeypatch.setattr(
            "src.media_import.importing.GDRIVE_DOWNLOAD_AS_ZIP_THRESHOLD", 0
        )

        root = GDriveRoot(
            "https://drive.google.com/drive/folders/1goqb4kHJHhxw4NASSd4vXMp6h04bansc"
        )
        mw = anki_session.mw
        _test_import(root, mw)


def test_mega_import(anki_session: AnkiSession) -> None:

    with anki_session.profile_loaded():
        from src.media_import.pathlike.mega import MegaRoot

        root = MegaRoot("https://mega.nz/folder/HzgAAZbI#ntmzJkB4N_2N0BXdzVUvXA")
        mw: Collection = anki_session.mw
        _test_import(root, mw)


def _test_import(root, mw: AnkiQt) -> None:
    from src.media_import.importing import ImportResult, import_media

    on_done_was_called = False

    media_dir = Path(mw.col.media.dir())

    def on_done(result: ImportResult):
        nonlocal on_done_was_called
        on_done_was_called = True
        assert result.success
        assert set(get_filenames_in_collection(media_dir)) == set(
            ["test1.png", "test2.png", "test3.jpg"]
        )

    import_media(root, on_done=on_done)

    # wait for the import to finish and for the on_done callback to be called
    taskman: TaskManager = mw.taskman
    taskman._executor.shutdown(wait=True)
    while taskman._closures:
        taskman._on_closures_pending()

    assert on_done_was_called


def get_filenames_in_collection(media_dir: Path) -> list[str]:
    return [x.name for x in media_dir.glob("*")]
