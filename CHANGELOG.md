# deflacue changelog

### v2.1.0 [2026-11-14]
* ++ Added delete_source option (--delete-source CLI flag) to remove source audio and .cue files after successful extraction (close #7).
* ++ Added use_bundle_path option (--no-bundle-path CLI flag) to write output files directly to the target path, without the Artist/Album directory structure (close #6).
* ** Target names are now sanitized on Windows: invalid characters, trailing dots and spaces are removed, fixing crashes on names like 'What I Have to Hide...' (close #4).

### v2.0.1 [2020-11-08]
* ** Fixed regression with missing track numbers in output files (see #2).

### v2.0.0 [2020-10-24]
* !! IMPORTANT: API changes (keyword-only args introduced).
* ++ Switched to improved .cue parser.
* ** Drop support for Py2 (3.6+ supported).

### v1.0.0
No changes, except version bumping up.

### v0.3.0
* ++ Added Py2 support.
* ++ Now installed into /usr/local/bin/ as deflacue
* ** Buggy -dry and -debug args renamed into --dry and --debug

### v0.2.0
* ++ Now splitting tracks with a frame precision.

### v0.1.0
* ++ Basic functionality.
