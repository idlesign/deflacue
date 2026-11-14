# Usage

## From Python

`from deflacue import deflacue` — if you want to use it as module.

Use `Deflacue` class for SoX interaction.

Use `CueParser` class for .cue parsing.

## From Command Line

`deflacue --help` in command line — to get help on utility usage.

In the following example we create audio collection in `/home/idle/audio_collection/` from audio CD images
stored under `/home/idle/audio_raw/` processing Cue Sheet files created using `windows-1251` encoding:

```shell
$ deflacue -e windows-1251 /home/idle/audio_raw/ -d /home/idle/audio_collection/
```

Useful options:

* `--delete-source` — delete source audio and .cue file(s) after successful extraction;
* `--no-bundle-path` — write output files directly to the target path, without the Artist/Album directory structure;
* `--dry` — dry run with no changes done to the filesystem.
