import pytest

from audio_spectrum import __version__
from audio_spectrum.__main__ import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_arguments_exits_cleanly():
    assert main([]) == 0
