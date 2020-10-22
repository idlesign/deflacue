"""
deflacue is a Cue Sheet parser and a wrapper for mighty SoX utility - http://sox.sourceforge.net/.

SoX with appropriate plugins should be installed for deflacue to function.
Ubuntu users may install the following SoX packages: `sox`, `libsox-fmt-all`.

deflacue can function both as a Python module and in command line mode.

"""
import logging
import os
from collections import defaultdict
from copy import deepcopy
from subprocess import Popen, PIPE
from typing import List, Dict

LOGGER = logging.getLogger('deflacue')

"""
COMMENTS_VORBIS = (
    'TITLE',
    'VERSION',
    'ALBUM',
    'TRACKNUMBER',
    'ARTIST',
    'PERFORMER',
    'COPYRIGHT',
    'LICENSE',
    'ORGANIZATION',
    'DESCRIPTION',
    'GENRE',
    'DATE',
    'LOCATION',
    'CONTACT',
    'ISRC',
)
"""

COMMENTS_CUE_TO_VORBIS = {
    'TRACK_NUM': 'TRACKNUMBER',
    'TITLE': 'TITLE',
    'PERFORMER': 'ARTIST',
    'ALBUM': 'ALBUM',
    'GENRE': 'GENRE',
    'DATE': 'DATE',
}


class DeflacueError(Exception):
    """Exception type raised by deflacue."""


class CueParser:
    """Simple Cue Sheet file parser."""

    def __init__(self, cue_file: str, *, encoding: str = None):
        """

        :param cue_file: .cue filepath
        :param encoding: file encoding

        """
        self._context_global = {
            'PERFORMER': 'Unknown',
            'SONGWRITER': None,
            'ALBUM': 'Unknown',
            'GENRE': 'Unknown',
            'DATE': None,
            'FILE': None,
            'COMMENT': None,
        }
        self._context_tracks = []

        self._current_context = self._context_global

        try:
            with open(cue_file, encoding=encoding) as f:
                lines = f.readlines()

        except UnicodeDecodeError:
            raise DeflacueError(
                'Unable to read data from .cue file. '
                'Please use -encoding command line argument to set correct encoding.'
            )

        for line in lines:
            line = line.strip()

            if not line:
                continue

            command, _, args = line.partition(' ')

            LOGGER.debug(f'Command `{command}`. Args: {args}')

            method = getattr(self, f'cmd_{command.lower()}', None)

            if method is None:
                LOGGER.warning(f'Unknown command `{command}`. Skipping ...')

            else:
                method(self._unquote(args))

        for idx, track_data in enumerate(self._context_tracks):
            track_end_pos = None

            try:
                track_end_pos = self._context_tracks[idx + 1]['POS_START_SAMPLES']

            except IndexError:
                pass

            track_data['POS_END_SAMPLES'] = track_end_pos

    def get_data_global(self) -> dict:
        """Returns a dictionary with global CD data."""
        return self._context_global

    def get_data_tracks(self) -> List[dict]:
        """Returns a list of dictionaries with individual
        tracks data. Note that some of the data is borrowed from global data.

        """
        return self._context_tracks

    @classmethod
    def _unquote(cls, val: str) -> str:
        return val.strip(' "')

    def _timestr_to_sec(self, timestr: str) -> int:
        """Converts `mm:ss:` time string into seconds integer."""
        splitted = timestr.split(':')[:-1]
        splitted.reverse()
        seconds = 0
        for i, chunk in enumerate(splitted, 0):
            factor = pow(60, i)
            if i == 0:
                factor = 1
            seconds += int(chunk) * factor
        return seconds

    def _timestr_to_samples(self, timestr: str) -> int:
        """Converts `mm:ss:ff` time string into samples integer, assuming the
        CD sampling rate of 44100Hz.

        """
        seconds_factor = 44100
        # 75 frames per second of audio
        frames_factor = seconds_factor // 75
        full_seconds = self._timestr_to_sec(timestr)
        frames = int(timestr.split(':')[-1])
        return full_seconds * seconds_factor + frames * frames_factor

    def _in_global_context(self) -> bool:
        return self._current_context == self._context_global

    def cmd_rem(self, args: str):
        subcommand, _, subargs = args.partition(' ')
        subargs = self._unquote(subargs)
        self._current_context[subcommand.upper()] = subargs

    def cmd_performer(self, args: str):
        self._current_context['PERFORMER'] = args

    def cmd_title(self, args: str):
        self._current_context['ALBUM' if self._in_global_context() else 'TITLE'] = args

    def cmd_file(self, args: str):
        filename = self._unquote(args.rsplit(' ', 1)[0])
        self._current_context['FILE'] = filename

    def cmd_index(self, args: str):
        timestr = args.split()[1]
        self._current_context['INDEX'] = timestr
        self._current_context['POS_START_SAMPLES'] = self._timestr_to_samples(timestr)

    def cmd_track(self, args: str):
        num, _ = args.split()
        new_track_context = deepcopy(self._context_global)
        self._context_tracks.append(new_track_context)
        self._current_context = new_track_context
        self._current_context['TRACK_NUM'] = int(num)

    def cmd_flags(self, args):
        pass


class Deflacue:
    """deflacue functionality is encapsulated in this class.

    Usage example:
        deflacue = Deflacue('/home/idle/cues_to_process/')
        deflacue.do()

    This will search `/home/idle/cues_to_process/` and subdirectories
    for .cue files, parse them and extract separate tracks.
    Extracted tracks are stored in Artist - Album hierarchy within
    `deflacue` directory under each source directory.

    """
    _dry_run = False  # Some lengthy shell command won't be executed on dry run.

    def __init__(
        self,
        source_path: str,
        *,
        dest_path: str = None,
        encoding: str = None,
        use_logging: int = logging.INFO
    ):
        """Prepares deflacue to for audio processing.

        :param source_path: Absolute or relative to the current directory path,
            containing .cue file(s) or subdirectories with .cue file(s) to process.

        :param dest_path: Absolute or relative to the current directory path
            to store output files in. If None, output files are saved in `deflacue` directory
            in the same directory as input file(s).

        :param encoding: Encoding used for .cue file(s).

        :param use_logging: Defines the verbosity level of deflacue. All messages
            produced by the application are logged with `logging` module.
            Examples: logging.INFO, logging.DEBUG.

        """
        src = os.path.abspath(source_path)
        self.path_source = src
        self.path_target = dest_path
        self.encoding = encoding

        if use_logging:
            self._configure_logging(use_logging)

        LOGGER.info(f'Source path: {src}')

        if not os.path.exists(src):
            raise DeflacueError(f'Path `{src}` is not found.')

        if dest_path is not None:
            self.path_target = os.path.abspath(dest_path)
            os.chdir(src)

    def _process_command(
        self,
        command: str,
        *,
        stdout=None,
        suppress_dry_run: bool = False
    ) -> int:
        """Executes shell command with subprocess.Popen.
        Returns status code.

        """
        LOGGER.debug(f'Executing shell command: {command}')

        if not self._dry_run or suppress_dry_run:
            prc = Popen(command, shell=True, stdout=stdout)
            prc.communicate()
            return prc.returncode

        return 0

    @classmethod
    def _configure_logging(cls, verbosity_lvl: int = logging.INFO):
        """Switches on logging at given level."""
        logging.basicConfig(level=verbosity_lvl, format='%(levelname)s: %(message)s')

    def _create_target_path(self, path: str):
        """Creates a directory for target files."""
        if self._dry_run:
            return

        LOGGER.debug(f'Creating target path: {path} ...')
        os.makedirs(path, exist_ok=True)

    def set_dry_run(self):
        """Sets deflacue into dry run mode, when all requested actions
        are only simulated, and no changes are written to filesystem.

        """
        self._dry_run = True

    def get_dir_files(self, *, recursive: bool = False) -> Dict[str, List[str]]:
        """Creates and returns dictionary of files in source directory.

        :param recursive: if True .cue search is also performed within subdirectories.

        """
        LOGGER.info(f'Enumerating files under the source path (recursive={recursive}) ...')

        files = {}
        if recursive:
            for current_dir, _, dir_files in os.walk(self.path_source):
                files[os.path.join(self.path_source, current_dir)] = [f for f in dir_files]

        else:
            files[self.path_source] = [
                f for f in os.listdir(self.path_source)
                if os.path.isfile(os.path.join(self.path_source, f))
            ]

        return files

    def filter_target_extensions(self, files_dict: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Takes file dictionary created with `get_dir_files` and returns
        dictionary of the same kind containing only audio files of supported
        types.

        :param files_dict:

        """
        files_filtered = defaultdict(list)
        LOGGER.info('Filtering .cue files ...')
        paths = files_dict.keys()

        for path in paths:

            if path.endswith('deflacue'):
                continue

            files = sorted(files_dict[path])
            for f in files:
                if os.path.splitext(f)[1] == '.cue':
                    files_filtered[path].append(f)

        return files_filtered

    def sox_check_is_available(self) -> bool:
        """Checks whether SoX is available."""
        result = self._process_command('sox -h', stdout=PIPE, suppress_dry_run=True)
        return result == 0

    def sox_extract_audio(
        self,
        *,
        source_file: str,
        pos_start_samples: int,
        pos_end_samples: int,
        target_file: str,
        metadata: Dict[str, str] = None
    ):
        """Using SoX extracts a chunk from source audio file into target.

        :param source_file: Source audio file path

        :param pos_start_samples: Trim position start (samples)

        :param pos_end_samples: Trim position end (samples)

        :param target_file: Trimmed audio file path

        :param metadata: Additional data (tags) dict.

        """
        LOGGER.info(f'Extracting `{os.path.basename(target_file)}` ...')

        chunk_length_samples = ''
        if pos_end_samples is not None:
            chunk_length_samples = f'{pos_end_samples - pos_start_samples}s'

        add_comment = ''
        if metadata is not None:
            LOGGER.debug(f'Metadata: {metadata}\n')

            for key, val in COMMENTS_CUE_TO_VORBIS.items():
                val_meta = metadata.get(key)
                if val_meta:
                    add_comment = f'--add-comment="{val}={val_meta}" {add_comment}'

        LOGGER.debug(
            'Extraction information:\n'
            f'      Source file: {source_file}\n'
            f'      Start position: {pos_start_samples} samples\n'
            f'      End position: {pos_end_samples} samples\n'
            f'      Length: {chunk_length_samples} sample(s)')

        command = (
            f'sox -V1 "{source_file}" '
            f'--comment="" {add_comment} "{target_file}" '
            f'trim {pos_start_samples}s {chunk_length_samples}'
        )

        self._process_command(command, stdout=PIPE)

    def process_cue(self, cue_file: str, target_path: str):
        """Parses .cue file, extracts separate tracks.

        :param cue_file: .cue filepath
        :param target_path: path to place files into

        """
        LOGGER.info(f'Processing `{os.path.basename(cue_file)}`\n')

        parser = CueParser(cue_file, encoding=self.encoding)
        cd_info = parser.get_data_global()

        if not os.path.exists(cd_info['FILE']):
            LOGGER.error(f"Source file `{cd_info['FILE']}` is not found. Cue Sheet is skipped.")
            return

        tracks = parser.get_data_tracks()

        title = cd_info['ALBUM']
        if cd_info['DATE'] is not None:
            title = f"{cd_info['DATE']} - {title}"

        bundle_path = os.path.join(target_path, cd_info['PERFORMER'], title)
        self._create_target_path(bundle_path)

        tracks_count = len(tracks)
        for track in tracks:

            track_num = str(track['TRACK_NUM']).rjust(len(str(tracks_count)), '0')
            filename = f"{track_num} - {track['TITLE'].replace('/', '')}.flac"

            self.sox_extract_audio(
                source_file=track['FILE'],
                pos_start_samples=track['POS_START_SAMPLES'],
                pos_end_samples=track['POS_END_SAMPLES'],
                target_file=os.path.join(bundle_path, filename),
                metadata=track
            )

    def do(self, *, recursive: bool = False):
        """Main method processing .cue files in batch.

        :param recursive: if True .cue search is also performed within subdirectories.

        """
        if self.path_target is not None:
            self._create_target_path(self.path_target)

        files_dict = self.filter_target_extensions(self.get_dir_files(recursive=recursive))

        dir_initial = os.getcwd()
        paths = sorted(files_dict.keys())

        for path in paths:
            os.chdir(path)

            LOGGER.info(f"\n{'====' * 10}\n      Working on: {path}\n")

            if self.path_target is None:
                # When a target path is not specified, create `deflacue` subdirectory
                # in every directory we are working at.
                target_path = os.path.join(path, 'deflacue')

            else:
                # When a target path is specified, we create a subdirectory there
                # named after the directory we are working on.
                target_path = os.path.join(self.path_target, os.path.split(path)[1])

            self._create_target_path(target_path)
            LOGGER.info(f'Target (output) path: {target_path}')

            for cue in files_dict[path]:
                self.process_cue(os.path.join(path, cue), target_path)

        os.chdir(dir_initial)

        LOGGER.info('We are done. Thank you.\n')
