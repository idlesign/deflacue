import logging
from collections import deque
from pathlib import Path

import pytest

from deflacue.deflacue import CueParser, Deflacue
from deflacue.exceptions import ParserError


class TestParser:

    def test_encoding(self, datafix_dir):

        fpath = datafix_dir / 'vys2.cue'

        with pytest.raises(ParserError):
            CueParser.from_file(fpath)

        parser = CueParser.from_file(fpath, encoding='cp1251')
        cue = parser.run()

        assert cue.meta.data == {
            'GENRE': 'Classic',
            'DATE': '2020',
            'COMMENT': 'Dumped',
            'PERFORMER': 'В. С. Высоцкий',
            'ALBUM': 'Пять песен',
        }

        assert len(cue.files) == 2
        assert str(cue.files[0]) == '01. Сторона А.flac'

        assert len(cue.tracks) == 5

        track = cue.tracks[3]
        assert str(track)
        assert track.start == 5426064
        assert track.end == 11205516
        assert track.data == {
            'ALBUM': 'Пять песен',
            'COMMENT': 'Dumped',
            'DATE': '2020',
            'GENRE': 'Classic',
            'INDEX 01': '02:03:03',
            'PERFORMER': 'В. С. Высоцкий',
            'TITLE': '04. Песня о вещей Кассандре'
        }
        track = cue.tracks[4]
        assert track.start == 11205516
        assert track.end == 0
        assert track.file.path == Path('02. Сторона В.flac')


@pytest.fixture
def sox_mock(monkeypatch):

    class SoxMock:

        def __init__(self):
            self.commands = []
            self.results = deque()

        def process_command(self, command, **kwargs):
            self.commands.append(command)
            return 0

    mock = SoxMock()
    monkeypatch.setattr('deflacue.deflacue.Deflacue._process_command', mock.process_command)

    return mock


class TestDeflacue:

    def test_basic(self, datafix_dir, sox_mock, tmp_path, caplog):

        caplog.set_level(logging.INFO, logger='deflacue')

        dest = tmp_path / 'sub'

        deflacue = Deflacue(
            source_path=str(datafix_dir),
            dest_path=str(dest),
            encoding='cp1251',
        )
        commands = sox_mock.commands

        available = deflacue.sox_check_is_available()
        assert available
        assert len(commands) == 1

        deflacue.do(recursive=True)
        assert len(commands) == 6

        assert (dest / 'datafixtures' / 'В. С. Высоцкий' / '2020 - Пять песен').exists()
        assert 'Extracting `5 - 05. История болезни.flac`' in caplog.text
