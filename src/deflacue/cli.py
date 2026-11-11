import argparse
import logging

from .deflacue import Deflacue, DeflacueError


def main():

    argparser = argparse.ArgumentParser('deflacue')

    argparser.add_argument(
        'source_path', help='Absolute or relative source path with .cue file(s).')
    argparser.add_argument(
        '-r', help='Recursion flag to search directories under the source_path.', action='store_true')
    argparser.add_argument(
        '-d', help='Absolute or relative destination path for output audio file(s).')
    argparser.add_argument(
        '-e', help='Cue Sheet file(s) encoding.')
    argparser.add_argument(
        '--dry', help='Perform the dry run with no changes done to filesystem.', action='store_true')
    argparser.add_argument(
        '--debug', help='Show debug messages while processing.', action='store_true')

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
            raise DeflacueError(
                'SoX seems not available. Please install it (e.g. `sudo apt-get install sox libsox-fmt-all`).'
            )

        if parsed.dry:
            deflacue.set_dry_run()

        deflacue.do(recursive=parsed.r)

    except DeflacueError as e:
        logging.error(e)
