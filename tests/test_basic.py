import logging
import re
from collections import deque
from pathlib import Path
from shutil import copy, copytree

import pytest

from deflacue.deflacue import CueParser, Deflacue, sanitize_name
from deflacue.exceptions import ParserError

RE_TARGET = re.compile(r'"([^"]+)"\s+trim')


class TestParser:

    def test_sanitize_name_posix(self):
        assert sanitize_name("a/b") == "ab"
        assert sanitize_name("What I Have to Hide...") == "What I Have to Hide..."

    def test_sanitize_name_windows(self, monkeypatch):
        monkeypatch.setattr("deflacue.deflacue.sys.platform", "win32")

        assert sanitize_name("What I Have to Hide...") == "What I Have to Hide"
        assert sanitize_name('a<b>c:d"e/f\\g|h?i*j ') == "abcdefghij"

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
            'TITLE': '04. Песня о вещей Кассандре',
            'TRACK_NUM': '4',
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
            logging.getLogger('deflacue').debug('Executing shell command: %s', command)
            self.commands.append(command)

            if self.results:
                return self.results.popleft()

            return 0

    mock = SoxMock()
    monkeypatch.setattr('deflacue.deflacue.Deflacue._process_command', mock.process_command)

    return mock


class TestDeflacue:

    def test_basic(self, datafix_dir, sox_mock, tmp_path, caplog):

        caplog.set_level(logging.DEBUG, logger='deflacue')

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
        caplog_text = caplog.text
        assert 'Extracting `5 - 05. История болезни.flac`' in caplog_text
        assert 'Еще Не Вечер.flac` is not found.' in caplog_text
        assert '--add-comment="TRACKNUMBER=4"' in caplog_text

    def test_delete_source(self, datafix_dir, sox_mock, tmp_path, caplog):

        caplog.set_level(logging.WARNING, logger="deflacue")

        work_dir = tmp_path / "in"
        copytree(datafix_dir, work_dir)

        deflacue = Deflacue(
            source_path=str(work_dir),
            dest_path=str(tmp_path / "out"),
            encoding="cp1251",
            delete_source=True,
        )
        deflacue.do()

        # vys1.cue references a missing audio file — its sources are kept;
        # vys2.cue was processed fine — its sources are deleted.
        assert (work_dir / "vys1.cue").exists()
        assert not (work_dir / "vys2.cue").exists()
        assert not (work_dir / "01. Сторона А.flac").exists()
        assert not (work_dir / "02. Сторона В.flac").exists()
        assert "Source files are kept" in caplog.text

    def test_delete_source_sox_failure(self, datafix_dir, sox_mock, tmp_path, caplog):

        work_dir = tmp_path / "in"
        work_dir.mkdir()

        for fname in ("vys2.cue", "01. Сторона А.flac", "02. Сторона В.flac"):
            copy(datafix_dir / fname, work_dir / fname)

        sox_mock.results.append(1)  # The first extraction fails.

        deflacue = Deflacue(
            source_path=str(work_dir),
            dest_path=str(tmp_path / "out"),
            encoding="cp1251",
            delete_source=True,
        )
        deflacue.do()

        assert (work_dir / "vys2.cue").exists()
        assert (work_dir / "01. Сторона А.flac").exists()
        assert "Source files are kept" in caplog.text

    def test_delete_source_dry_run(self, datafix_dir, sox_mock, tmp_path):

        work_dir = tmp_path / "in"
        copytree(datafix_dir, work_dir)

        deflacue = Deflacue(
            source_path=str(work_dir),
            dest_path=str(tmp_path / "out"),
            encoding="cp1251",
            delete_source=True,
        )
        deflacue.set_dry_run()
        deflacue.do()

        assert (work_dir / "vys2.cue").exists()
        assert (work_dir / "01. Сторона А.flac").exists()

    def test_no_bundle_path(self, datafix_dir, sox_mock, tmp_path):

        dest = tmp_path / "out"
        deflacue = Deflacue(
            source_path=str(datafix_dir),
            dest_path=str(dest),
            encoding="cp1251",
            use_bundle_path=False,
        )
        deflacue.do()

        # sox is mocked, so we check the target paths it was called with:
        # files should land right in the target directory, without the Artist/Album structure.
        targets = [RE_TARGET.search(command).group(1) for command in sox_mock.commands if "trim" in command]

        assert targets
        assert all(Path(target).parent == dest for target in targets)
