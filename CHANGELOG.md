# Changelog

## 0.2.0 (unreleased)

First versioned release of the modernized script. The original prototype-era
script is tagged `v0.1.0`.

### Changed
- Requires Python 3.6 or later; the shebang now runs `python3`.
- Command-line interface moved to argparse: `--help`, `--version`, `--status`
  (report fan speeds without changing them), `--device` (skip auto-discovery),
  and `--sg-ses` (path to the sg_ses binary).

### Fixed
- The `sg_ses_path` environment variable (and the new `--sg-ses` flag) is now
  honored when reading and writing the enclosure control page, not just during
  enclosure discovery. Previously, setting fan speeds always invoked `sg_ses`
  from `PATH`.

### Added
- Test suite (pytest) and GitHub Actions CI with linting (ruff) across
  Python 3.9–3.13.
