import pytest


@pytest.fixture(autouse=True)
def user_presets(tmp_path, monkeypatch):
    """Every test gets an empty user preset folder, never the real one."""
    folder = tmp_path / "user-presets"
    monkeypatch.setenv("AUDIO_SPECTRUM_PRESET_DIR", str(folder))
    return folder
