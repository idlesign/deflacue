from collections import deque

import pytest

from deflacue.deflacue import CueParser, DeflacueError, Deflacue


class TestParser:

    def test_encoding(self, datafix_dir):

        fpath = str(datafix_dir / 'vys2.cue')

        with pytest.raises(DeflacueError):
            CueParser(fpath)

        parser = CueParser(fpath, encoding='cp1251')

        data_global = parser.get_data_global()
        assert data_global == {
            'ALBUM': 'Пять песен',
            'COMMENT': 'Dumped',
            'DATE': '2020',
            'FILE': '01. Сторона А.flac',
            'GENRE': 'Classic',
            'PERFORMER': 'В. С. Высоцкий',
            'SONGWRITER': None
       }

        data_tracks = parser.get_data_tracks()
        assert data_tracks == [
            {
                'ALBUM': 'Пять песен',
                'COMMENT': 'Dumped',
                'DATE': '2020',
                'FILE': '01. Сторона А.flac',
                'GENRE': 'Classic',
                'INDEX': '00:00:00',
                'PERFORMER': 'В. С. Высоцкий',
                'POS_END_SAMPLES': 13013028,
                'POS_START_SAMPLES': 0,
                'SONGWRITER': None,
                'TITLE': '01. Песня о погибшем лётчике',
                'TRACK_NUM': 1
            },
            {
                'ALBUM': 'Пять песен',
                'COMMENT': 'Dumped',
                'DATE': '2020',
                'FILE': '02. Сторона В.flac',  # todo bogus
                'GENRE': 'Classic',
                'INDEX': '04:55:06',
                'PERFORMER': 'В. С. Высоцкий',
                'POS_END_SAMPLES': 0,
                'POS_START_SAMPLES': 13013028,
                'SONGWRITER': None,
                'TITLE': '02. Дом Хрустальный',
                'TRACK_NUM': 2
            },
            {
                'ALBUM': 'Пять песен',
                'COMMENT': 'Dumped',
                'DATE': '2020',
                'FILE': '01. Сторона А.flac',  # todo bogus
                'GENRE': 'Classic',
                'INDEX': '00:00:00',
                'PERFORMER': 'В. С. Высоцкий',
                'POS_END_SAMPLES': 5426064,
                'POS_START_SAMPLES': 0,
                'SONGWRITER': None,
                'TITLE': '03. Песня Бродского',
                'TRACK_NUM': 3
            },
            {
                'ALBUM': 'Пять песен',
                'COMMENT': 'Dumped',
                'DATE': '2020',
                'FILE': '01. Сторона А.flac',  # todo bogus
                'GENRE': 'Classic',
                'INDEX': '02:03:03',
                'PERFORMER': 'В. С. Высоцкий',
                'POS_END_SAMPLES': 11205516,
                'POS_START_SAMPLES': 5426064,
                'SONGWRITER': None,
                'TITLE': '04. Песня о вещей Кассандре',
                'TRACK_NUM': 4
            },
            {
                'ALBUM': 'Пять песен',
                'COMMENT': 'Dumped',
                'DATE': '2020',
                'FILE': '01. Сторона А.flac',  # todo bogus
                'GENRE': 'Classic',
                'INDEX': '04:14:07',
                'PERFORMER': 'В. С. Высоцкий',
                'POS_END_SAMPLES': None,
                'POS_START_SAMPLES': 11205516,
                'SONGWRITER': None,
                'TITLE': '05. История болезни',
                'TRACK_NUM': 5
            }
        ]


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

    def test_basic(self, datafix_dir, sox_mock, tmp_path):

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
