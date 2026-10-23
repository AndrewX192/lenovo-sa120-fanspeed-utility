# Changelog

## 0.2.0 (2026-10-22)

First versioned release of the modernized script. The original prototype-era
script is tagged `v0.1.0`.

### Changed
- Requires Python 3.6 or later; the shebang now runs `python3`.
- Command-line interface moved to argparse: `--help`, `--version`, `--status`
  (report fan speeds without changing them), `--device` (skip auto-discovery),
  and `--sg-ses` (path to the sg_ses binary).

### Fixed
- A failed enclosure control write (e.g. running without root) now exits
  non-zero and prints sg_ses's error, instead of reporting success.
- Devices named with `--device` are verified to be SA120 enclosures before
  the control page is written, and nodes aliasing the same enclosure are
  only programmed once.
- An unexpectedly short enclosure control page is reported as an error
  instead of crashing with an IndexError; sg_ses failures in general print
  a message rather than a Python traceback.
- `--maxlen=32768` is now passed to `sg_ses` only when the binary supports
  it (sg3_utils 1.38 and later). Older builds, such as the one shipped with
  CentOS 7, rejected the option, which made every enclosure report
  "Enclosure not found". The cap is kept where available because FreeBSD
  terminates SES requests whose response exceeds 65535 bytes. (#13, #14)
- A missing or unrunnable `sg_ses` binary now produces a clear error
  message instead of a traceback.
- The `sg_ses_path` environment variable (and the new `--sg-ses` flag) is now
  honored when reading and writing the enclosure control page, not just during
  enclosure discovery. Previously, setting fan speeds always invoked `sg_ses`
  from `PATH`.

### Added
- Test suite (pytest) and GitHub Actions CI with linting (ruff) across
  Python 3.9–3.13.
