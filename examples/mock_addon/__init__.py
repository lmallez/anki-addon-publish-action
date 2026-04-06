try:
    from aqt.gui_hooks import main_window_did_init
    from aqt.utils import showInfo
except ImportError:
    main_window_did_init = None
    showInfo = None


def on_main_window_ready() -> None:
    if showInfo is not None:
        showInfo("Mock upload test add-on loaded successfully.")


if main_window_did_init is not None:
    main_window_did_init.append(on_main_window_ready)
