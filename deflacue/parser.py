import logging
from copy import deepcopy
from pathlib import Path
from typing import List, Optional, Tuple

from .exceptions import ParserError

LOGGER = logging.getLogger(__name__)


def pos_to_frames(pos) -> int:
    """Converts position (mm:ss:ff) into frames.

    :param pos:

    """
    minutes, seconds, frames = map(int, pos.split(':'))
    seconds = (minutes * 60) + seconds
    rate = 44100
    return (seconds * rate) + (frames * (rate // 75))


class Context:
    """Basic context."""

    _default = {}

    def __init__(self, *, data: dict):
        self.data = {**self._default, **deepcopy(data)}

    def add(self, key: str, val: str):
        self.data[key] = val


class MetaContext(Context):
    """Global .cue meta context."""

    _default = {
        'ALBUM': 'Unknown',
        'PERFORMER': 'Unknown',
        'DATE': None,
    }

    def add(self, key: str, val: str):
        if key == 'TITLE':
            key = 'ALBUM'
        super().add(key, val)


class FileContext(Context):
    """File information."""

    def __init__(self, *, path: str, ftype: str, data: dict):
        self.path: Path = Path(path)
        """File path."""

        self.type = ftype
        """File type."""

        self.tracks: List[TrackContext] = []
        """Tracks in file."""

        super().__init__(data=data)

    def __str__(self):
        return str(self.path)


class TrackContext(Context):
    """Track information."""

    _default = {
        'TITLE': 'Unknown',
    }

    def __init__(self, *, file: FileContext, num: int, dtype: str):
        self.file = file
        """File containing track."""

        self.num = num
        """Track number."""

        self.type = dtype
        """Track data type."""

        self.start: int = 0
        """Start position (frames)."""

        super().__init__(data=file.data)

    def __str__(self):
        return f"{self.num} {self.title} @ {self.file}"

    @property
    def title(self):
        return self.data.get('TITLE', '')

    @property
    def end(self) -> int:
        tracks = self.file.tracks
        end = 0

        for idx, track in enumerate(tracks):
            if track is self:
                try:
                    end = tracks[idx+1].start

                except IndexError:
                    pass

                break

        return end


class CueData:
    """Represents data from .cue file."""

    def __init__(self):
        self.meta = []

        self.meta = MetaContext(data={})
        """Basic information."""

        self.files: List[FileContext] = []
        """Files in image."""

        self.tracks: List[TrackContext] = []
        """Tracks in image."""

        self._current_file: Optional[FileContext] = None
        self._current_track: Optional[TrackContext] = None
        self._current_context: Context = self.meta

    def add_context(self, key, val):
        self._current_context.add(key, val)

    def add_file(self, *, path: str, ftype: str):
        file_context = FileContext(
            path=path,
            ftype=ftype,
            data=self._current_context.data
        )
        self._current_context = file_context
        self._current_file = file_context
        self.files.append(file_context)

    def add_track(self, *, num: int, dtype: str):
        file_context = self._current_file
        track_context = TrackContext(
            file=self._current_file,
            num=num,
            dtype=dtype,
        )
        file_context.tracks.append(track_context)
        self._current_context = track_context
        self._current_track = track_context
        self.tracks.append(track_context)

    def add_track_index(self, *, pos: str):
        self._current_track.start = pos_to_frames(pos)


class CueParser:
    """Simple Cue Sheet file parser."""

    def __init__(self, lines: List[str]):
        self.lines = lines

    def run(self) -> CueData:

        cue = CueData()
        parse_cmd = self._parse_command
        unquote = self._unquote

        for line in self.lines:
            cmd, args = parse_cmd(line)

            if cmd == 'REM':
                cue.add_context(*parse_cmd(args))

            elif cmd == 'FILE':
                fpath, ftype = args.rsplit(' ', 1)
                fpath = unquote(fpath)
                cue.add_file(path=fpath, ftype=ftype)

            elif cmd == 'TRACK':
                num, _, dtype = args.partition(' ')
                cue.add_track(num=int(num), dtype=dtype)

            elif cmd == 'INDEX':
                num, _, pos = args.partition(' ')

                if num == '01':
                    cue.add_context(f'{cmd} {num}', pos)
                    cue.add_track_index(pos=pos)

            else:
                cue.add_context(cmd, args)

        return cue

    def _parse_command(self, cmd: str) -> Tuple[str, str]:
        command, _, args = cmd.partition(' ')
        args = self._unquote(args)

        LOGGER.debug(f'Parsed command `{command}`. Args: {args}')

        return command, args

    @classmethod
    def _unquote(cls, val: str) -> str:
        return val.strip(' "')

    @classmethod
    def from_file(cls, fpath: Path, *, encoding: str = None) -> 'CueParser':

        def read(coding: str = None) -> Optional[CueParser]:

            try:
                with open(str(fpath), encoding=coding) as f:
                    return CueParser([
                        line.strip() for line in f.readlines()
                        if line.strip()
                    ])

            except UnicodeDecodeError:
                return None

        parser = read(encoding)

        if not parser:
            # Try unicode as a fallback.
            parser = read()

        if not parser:
            raise ParserError(
                'Unable to read data from .cue file. '
                'Please provide a correct encoding.'
            )

        return parser
