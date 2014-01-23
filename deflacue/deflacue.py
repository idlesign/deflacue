#!/usr/bin/env python
"""
deflacue is a Cue Sheet parser and a wrapper for mighty SoX utility - http://sox.sourceforge.net/.

SoX with appropriate plugins should be installed for deflacue to function.
Ubuntu users may install the following SoX packages: `sox`, `libsox-fmt-all`.


deflacue can function both as a Python module and in command line mode.
"""
import os
import logging
import argparse

from io import open  # Py2 support
from copy import deepcopy
from collections import defaultdict
from subprocess import Popen, PIPE


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
    'ISRC'
)

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


class CueParser(object):
    """Simple Cue Sheet file parser."""

    def __init__(self, cue_file, encoding=None):
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
            raise DeflacueError('Unable to read data from .cue file. Please use -encoding command line argument to set correct encoding.')

        for line in lines:
            if line.strip():
                command, args = line.strip().split(' ', 1)
                logging.debug('Command `%s`. Args: %s' % (command, args))
                method = getattr(self, 'cmd_%s' % command.lower(), None)
                if method is not None:
                    method(args)
                else:
                    logging.warning('Unknown command `%s`. Skipping ...' % command)

        for idx, track_data in enumerate(self._context_tracks):
            track_end_pos = None
            try:
                track_end_pos = self._context_tracks[idx + 1]['POS_START_SAMPLES']
            except IndexError:
                pass
            track_data['POS_END_SAMPLES'] = track_end_pos

    def get_data_global(self):
        """Returns a dictionary with global CD data."""
        return self._context_global

    def get_data_tracks(self):
        """Returns a list of dictionaries with individual
        tracks data. Note that some of the data is borrowed from global data.

        """
        return self._context_tracks

    def _unquote(self, in_str):
        return in_str.strip(' "')

    def _timestr_to_sec(self, timestr):
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

    def _timestr_to_samples(self, timestr):
        """Converts `mm:ss:ff` time string into samples integer, assuming the
        CD sampling rate of 44100Hz."""
        seconds_factor = 44100
        # 75 frames per second of audio
        frames_factor = seconds_factor // 75
        full_seconds = self._timestr_to_sec(timestr)
        frames = int(timestr.split(':')[-1])
        return full_seconds * seconds_factor + frames * frames_factor

    def _in_global_context(self):
        return self._current_context == self._context_global

    def cmd_rem(self, args):
        subcommand, subargs = args.split(' ', 1)
        if subargs.startswith('"'):
            subargs = self._unquote(subargs)
        self._current_context[subcommand.upper()] = subargs

    def cmd_performer(self, args):
        unquoted = self._unquote(args)
        self._current_context['PERFORMER'] = unquoted

    def cmd_title(self, args):
        unquoted = self._unquote(args)
        if self._in_global_context():
            self._current_context['ALBUM'] = unquoted
        else:
            self._current_context['TITLE'] = unquoted

    def cmd_file(self, args):
        filename = self._unquote(args.rsplit(' ', 1)[0])
        self._current_context['FILE'] = filename

    def cmd_index(self, args):
        timestr = args.split()[1]
        self._current_context['INDEX'] = timestr
        self._current_context['POS_START_SAMPLES'] = self._timestr_to_samples(timestr)

    def cmd_track(self, args):
        num, ttype = args.split()
        new_track_context = deepcopy(self._context_global)
        self._context_tracks.append(new_track_context)
        self._current_context = new_track_context
        self._current_context['TRACK_NUM'] = int(num)

    def cmd_flags(self, args):
        pass


class Deflacue(object):
    """deflacue functionality is encapsulated in this class.

    Usage example:
        deflacue = Deflacue('/home/idle/cues_to_process/')
        deflacue.do()

    This will search `/home/idle/cues_to_process/` and subdirectories
    for .cue files, parse them and extract separate tracks.
    Extracted tracks are stored in Artist - Album hierarchy within
    `deflacue` directory under each source directory.

    """

    # Some lengthy shell command won't be executed on dry run.
    _dry_run = False

    def __init__(self, source_path, dest_path=None, encoding=None, use_logging=logging.INFO):
        """Prepares deflacue to for audio processing.

        `source_path` - Absolute or relative to the current directory path,
                        containing .cue file(s) or subdirectories with
                        .cue file(s) to process.

        `dest_path`   - Absolute or relative to the current directory path
                        to store output files in.
                        If None, output files are saved in `deflacue` directory
                        in the same directory as input file(s).

        `encoding`    -  Encoding used for .cue file(s).

        `use_logging` - Defines the verbosity level of deflacue. All messages
                        produced by the application are logged with `logging` module.
                        Examples: logging.INFO, logging.DEBUG.

        """
        self.path_source = os.path.abspath(source_path)
        self.path_target = dest_path
        self.encoding = encoding

        if use_logging:
            self._configure_logging(use_logging)

        logging.info('Source path: %s' % self.path_source)
        if not os.path.exists(self.path_source):
            raise DeflacueError('Path `%s` is not found.' % self.path_source)

        if dest_path is not None:
            self.path_target = os.path.abspath(dest_path)
            os.chdir(self.path_source)

    def _process_command(self, command, stdout=None, supress_dry_run=False):
        """Executes shell command with subprocess.Popen.
        Returns tuple, where first element is a process return code,
        and the second is a tuple of stdout and stderr output.
        """
        logging.debug('Executing shell command: %s' % command)
        if (self._dry_run and supress_dry_run) or not self._dry_run:
            prc = Popen(command, shell=True, stdout=stdout)
            std = prc.communicate()
            return prc.returncode, std
        return 0, ('', '')

    def _configure_logging(self, verbosity_lvl=logging.INFO):
        """Switches on logging at given level."""
        logging.basicConfig(level=verbosity_lvl, format='%(levelname)s: %(message)s')

    def _create_target_path(self, path):
        """Creates a directory for target files."""
        if not os.path.exists(path) and not self._dry_run:
            logging.debug('Creating target path: %s ...' % path)
            try:
                os.makedirs(path)
            except OSError:
                raise DeflacueError('Unable to create target path: %s.' % path)

    def set_dry_run(self):
        """Sets deflacue into dry run mode, when all requested actions
        are only simulated, and no changes are written to filesystem.

        """
        self._dry_run = True

    def get_dir_files(self, recursive=False):
        """Creates and returns dictionary of files in source directory.
        `recursive` - if True search is also performed within subdirectories.

        """
        logging.info('Enumerating files under the source path (recursive=%s) ...' % recursive)
        files = {}
        if not recursive:
            files[self.path_source] = [file for file in os.listdir(self.path_source) if os.path.isfile(os.path.join(self.path_source, file))]
        else:
            for current_dir, sub_dirs, dir_files in os.walk(self.path_source):
                files[os.path.join(self.path_source, current_dir)] = [file for file in dir_files]

        return files

    def filter_target_extensions(self, files_dict):
        """Takes file dictionary created with `get_dir_files` and returns
        dictionary of the same kind containing only audio files of supported
        types.

        """
        files_filtered = defaultdict(list)
        logging.info('Filtering .cue files ...')
        paths = files_dict.keys()

        for path in paths:
            if not path.endswith('deflacue'):
                files = sorted(files_dict[path])
                for file in files:
                    if os.path.splitext(file)[1] == '.cue':
                        files_filtered[path].append(file)
        return files_filtered

    def sox_check_is_available(self):
        """Checks whether SoX is available."""
        result = self._process_command('sox -h', PIPE, supress_dry_run=True)
        return result[0] == 0

    def sox_extract_audio(self, source_file, pos_start_samples, pos_end_samples, target_file, metadata=None):
        """Using SoX extracts a chunk from source audio file into target."""
        logging.info('Extracting `%s` ...' % os.path.basename(target_file))

        chunk_length_samples = ''
        if pos_end_samples is not None:
            chunk_length_samples = "%ss" % (pos_end_samples - pos_start_samples)

        add_comment = ''
        if metadata is not None:
            logging.debug('Metadata: %s\n' % metadata)
            for key, val in COMMENTS_CUE_TO_VORBIS.items():
                if key in metadata and metadata[key] is not None:
                    add_comment = '--add-comment="%s=%s" %s' % (val, metadata[key], add_comment)

        logging.debug('Extraction information:\n'
                     '      Source file: %(source)s\n'
                     '      Start position: %(pos_start)s samples\n'
                     '      End position: %(pos_end)s samples\n'
                     '      Length: %(length)s sample(s)' %
                     {'source': source_file, 'pos_start': pos_start_samples, 'pos_end': pos_end_samples, 'length': chunk_length_samples})

        command = 'sox -V1 "%(source)s" --comment="" %(add_comment)s "%(target)s" trim %(start_pos)ss %(length)s' % {
            'source': source_file, 'target': target_file, 'start_pos': pos_start_samples, 'length': chunk_length_samples,
            'add_comment': add_comment}

        if not self._dry_run:
            self._process_command(command, PIPE)

    def process_cue(self, cue_file, target_path):
        """Parses .cue file, extracts separate tracks."""
        logging.info('Processing `%s`\n' % os.path.basename(cue_file))
        parser = CueParser(cue_file, encoding=self.encoding)
        cd_info = parser.get_data_global()

        if not os.path.exists(cd_info['FILE']):
            logging.error('Source file `%s` is not found. Cue Sheet is skipped.' % cd_info['FILE'])
            return

        tracks = parser.get_data_tracks()

        title = cd_info['ALBUM']
        if cd_info['DATE'] is not None:
            title = '%s - %s' % (cd_info['DATE'], title)

        try:  # Py2 support
            target_path = target_path.decode('utf-8')
        except AttributeError:
            pass

        bundle_path = os.path.join(target_path, cd_info['PERFORMER'], title)
        self._create_target_path(bundle_path)

        tracks_count = len(tracks)
        for track in tracks:
            track_num = str(track['TRACK_NUM']).rjust(len(str(tracks_count)), '0')
            filename = '%s - %s.flac' % (track_num, track['TITLE'].replace('/', ''))
            self.sox_extract_audio(track['FILE'], track['POS_START_SAMPLES'], track['POS_END_SAMPLES'], os.path.join(bundle_path, filename), metadata=track)

    def do(self, recursive=False):
        """Main method processing .cue files in batch."""
        if self.path_target is not None and not os.path.exists(self.path_target):
            self._create_target_path(self.path_target)

        files_dict = self.filter_target_extensions(self.get_dir_files(recursive))

        dir_initial = os.getcwd()
        paths = sorted(files_dict.keys())
        for path in paths:
            os.chdir(path)
            logging.info('\n%s\n      Working on: %s\n' % ('====' * 10, path))

            if self.path_target is None:
                # When a target path is not specified, create `deflacue` subdirectory
                # in every directory we are working at.
                target_path = os.path.join(path, 'deflacue')
            else:
                # When a target path is specified, we create a subdirectory there
                # named after the directory we are working on.
                target_path = os.path.join(self.path_target, os.path.split(path)[1])

            self._create_target_path(target_path)
            logging.info('Target (output) path: %s' % target_path)

            for cue in files_dict[path]:
                self.process_cue(os.path.join(path, cue), target_path)

        os.chdir(dir_initial)

        logging.info('We are done. Thank you.\n')


def main():

    argparser = argparse.ArgumentParser('deflacue.py')

    argparser.add_argument('source_path', help='Absolute or relative source path with .cue file(s).')
    argparser.add_argument('-r', help='Recursion flag to search directories under the source_path.', action='store_true')
    argparser.add_argument('-d', help='Absolute or relative destination path for output audio file(s).')
    argparser.add_argument('-e', help='Cue Sheet file(s) encoding.')
    argparser.add_argument('--dry', help='Perform the dry run with no changes done to filesystem.', action='store_true')
    argparser.add_argument('--debug', help='Show debug messages while processing.', action='store_true')

    parsed = argparser.parse_args()
    kwargs = {'source_path': parsed.source_path}

    if parsed.e is not None:
        kwargs['encoding'] = parsed.e

    if parsed.d is not None:
        kwargs['dest_path'] = parsed.d

    if parsed.debug:
        kwargs['use_logging'] = logging.DEBUG

    try:
        deflacue = Deflacue(**kwargs)

        if not deflacue.sox_check_is_available():
            raise DeflacueError('SoX seems not available. Please install it (e.g. `sudo apt-get install sox libsox-fmt-all`).')

        if parsed.dry:
            deflacue.set_dry_run()

        deflacue.do(parsed.r)
    except DeflacueError as e:
        logging.error(e)


if __name__ == '__main__':
    main()
