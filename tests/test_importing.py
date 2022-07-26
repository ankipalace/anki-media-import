from pathlib import Path

from anki.collection import Collection
from pytest_anki import AnkiSession

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def test_local_import(anki_session: AnkiSession) -> None:

    with anki_session.profile_loaded():
        from src.media_import.importing import ImportResult, import_media
        from src.media_import.pathlike.local import LocalRoot

        root = LocalRoot(TEST_DATA_DIR)
        col = anki_session.mw.col

        def on_done(result: ImportResult):
            assert result.success
            assert [x.name for x in Path(col.media.dir()).glob("*")] == ["image.jpg"]

        import_media(root, on_done=on_done)


def test_gdrive_import(anki_session: AnkiSession) -> None:

    with anki_session.profile_loaded():
        from src.media_import.importing import ImportResult, import_media
        from src.media_import.pathlike.gdrive import GDriveRoot

        root = GDriveRoot(
            "https://drive.google.com/drive/folders/1HvAotOC1Qo7JeNNfBrc_9ExG7dAGV6eG?usp=sharing"
        )
        col = anki_session.mw.col

        def on_done(result: ImportResult):
            assert result.success
            print(get_filenames_in_collection(col))
            assert set(get_filenames_in_collection(col)) == set(['test1.png', 'test2.png', 'test3.jpg'])

        import_media(root, on_done=on_done)


def get_filenames_in_collection(col: Collection):
    return [x.name for x in Path(col.media.dir()).glob("*")]


# from src.media_import.pathlike.gdrive import GDriveRoot
# from src.media_import.pathlike.mega import MegaRoot
