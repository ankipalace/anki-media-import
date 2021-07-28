from pathlib import Path

from .ankiaddonconfig import ConfigManager, ConfigWindow, ConfigLayout
from .importing import import_media

conf = ConfigManager()


def on_save() -> None:
    path = Path(conf.get("path"))
    print("importing from {}".format(path))
    import_media(path)


def default_tab(conf_window: ConfigWindow) -> None:
    # Temporary!
    tab = conf_window.add_tab("General")
    tab.path_input("path", "Path to import", get_directory=True)
    conf_window.execute_on_save(on_save)


conf.use_custom_window()
conf.add_config_tab(default_tab)
