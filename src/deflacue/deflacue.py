"""
deflacue is a Cue Sheet parser and a wrapper for mighty SoX utility - http://sox.sourceforge.net/.

SoX with appropriate plugins should be installed for deflacue to function.
Ubuntu users may install the following SoX packages: `sox`, `libsox-fmt-all`.

deflacue can function both as a Python module and in command line mode.

"""
import logging
import os
from collections import defaultdict
from pathlib import Path
from subprocess import Popen, PIPE
from typing import List, Dict, Union, Optional

from .exceptions import DeflacueError
from .parser import CueParser

LOGGER = logging.getLogger(__name__)
TypePath = Union[str, Path]


COMMENTS_CUE_TO_VORBIS = {
    'TRACK_NUM': 'TRACKNUMBER',
    'TITLE': 'TITLE',
    'PERFORMER': 'ARTIST',
    'ALBUM': 'ALBUM',
    'GENRE': 'GENRE',
    'DATE': 'DATE',
    'ISRC': 'ISRC',
    'COMMENT': 'DESCRIPTION',
}
"""Cue REM commands to Vorbis tags."""


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
    _target_default = 'deflacue'

    def __init__(
        self,
        source_path: TypePath,
        *,
        dest_path: TypePath = None,
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
        src = Path(source_path).absolute()
        self.path_source: Path = src
        self.path_target: Optional[Path] = dest_path
        self.encoding = encoding

        if use_logging:
            self._configure_logging(use_logging)

        LOGGER.info(f'Source path: {src}')

        if not src.exists():
            raise DeflacueError(f'Path `{src}` is not found.')

        if dest_path is not None:
            self.path_target = Path(dest_path).absolute()
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

    def _create_target_path(self, path: Optional[Path]):
        """Creates a directory for target files."""
        if self._dry_run or not path:
            return

        LOGGER.debug(f'Creating target path: {path} ...')
        os.makedirs(path, exist_ok=True)

    def set_dry_run(self):
        """Sets deflacue into dry run mode, when all requested actions
        are only simulated, and no changes are written to filesystem.

        """
        self._dry_run = True

    def get_dir_files(self, *, recursive: bool = False) -> Dict[Path, List[Path]]:
        """Creates and returns dictionary of files in source directory.

        :param recursive: if True search is also performed within subdirectories.

        """
        LOGGER.info(f'Enumerating files under the source path (recursive={recursive}) ...')

        files = {}
        if recursive:
            for current_dir, _, dir_files in os.walk(self.path_source):
                path = self.path_source / current_dir
                files[path] = [path / f for f in dir_files]

        else:
            files[self.path_source] = [
                f for f in self.path_source.iterdir()
                if f.is_file()
            ]

        return files

    def filter_target_extensions(self, files_dict: Dict[Path, List[Path]]) -> Dict[Path, List[Path]]:
        """Takes file dictionary created with `get_dir_files` and returns
        dictionary of the same kind containing only files of supported
        types.

        :param files_dict:

        """
        files_filtered = defaultdict(list)
        LOGGER.info('Filtering .cue files ...')
        paths = files_dict.keys()

        for path in paths:

            if path.name == self._target_default:
                continue

            for f in sorted(files_dict[path]):
                if f.suffix == '.cue':
                    files_filtered[path].append(f)

        return files_filtered

    def sox_check_is_available(self) -> bool:
        """Checks whether SoX is available."""
        result = self._process_command('sox -h', stdout=PIPE, suppress_dry_run=True)
        return result == 0

    def sox_extract_audio(
        self,
        *,
        source_file: Path,
        pos_start_samples: int,
        pos_end_samples: int,
        target_file: Path,
        metadata: Dict[str, str] = None
    ):
        """Using SoX extracts a chunk from source audio file into target.

        :param source_file: Source audio file path

        :param pos_start_samples: Trim position start (samples)

        :param pos_end_samples: Trim position end (samples)

        :param target_file: Trimmed audio file path

        :param metadata: Additional data (tags) dict.

        """
        LOGGER.info(f'  Extracting `{target_file.name}` ...')

        chunk_length_samples = ''
        if pos_end_samples:
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

    def process_cue(self, *, cue_file: Path, target_path: Path):
        """Parses .cue file, extracts separate tracks.

        :param cue_file: .cue filepath

        :param target_path: path to place files into

        """
        LOGGER.info(f'\nProcessing `{cue_file.name}`\n')

        parser = CueParser.from_file(fpath=cue_file, encoding=self.encoding)
        cue = parser.run()

        cd_info = cue.meta.data
        tracks = cue.tracks

        def sanitize(val: str) -> str:
            return val.replace('/', '')

        title = cd_info['ALBUM']
        if cd_info['DATE'] is not None:
            title = f"{cd_info['DATE']} - {title}"

        bundle_path = target_path / sanitize(cd_info['PERFORMER']) / sanitize(title)
        self._create_target_path(bundle_path)

        len_tracks_count = len(str(len(tracks)))
        for track in tracks:
            track_file = track.file.path

            if not track_file.exists():
                LOGGER.error(f'Source file `{track_file}` is not found. Track is skipped.')
                continue

            track_num = str(track.num).rjust(len_tracks_count, '0')
            filename = f"{track_num} - {sanitize(track.title)}.flac"

            self.sox_extract_audio(
                source_file=track_file,
                pos_start_samples=track.start,
                pos_end_samples=track.end,
                target_file=bundle_path / filename,
                metadata=track.data
            )

    def do(self, *, recursive: bool = False):
        """Main method processing .cue files in batch.

        :param recursive: if True .cue search is also performed within subdirectories.

        """
        self._create_target_path(self.path_target)

        files_dict = self.filter_target_extensions(self.get_dir_files(recursive=recursive))

        dir_initial = os.getcwd()
        paths = sorted(files_dict.keys())

        for path in paths:
            os.chdir(path)

            LOGGER.info(f"\n{'====' * 10}\nWorking on: {path}\n")

            if self.path_target is None:
                # When a target path is not specified, create `deflacue` subdirectory
                # in every directory we are working at.
                target_path = path / self._target_default

            else:
                # When a target path is specified, we create a subdirectory there
                # named after the directory we are working on.
                target_path = self.path_target / path.name

            self._create_target_path(target_path)

            LOGGER.info(f'Target (output) path: {target_path}')

            for cue in files_dict[path]:
                self.process_cue(cue_file=path / cue, target_path=target_path)

        os.chdir(dir_initial)

        LOGGER.info('We are done. Thank you.\n')
