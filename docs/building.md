# Building the Package

## Overview
Instructions for building and installing the APRS Rover Library package.

## Building
Install build tools:
```sh
pip install build
```

Build the package:
```sh
python -m build
```
This will create a `dist/` directory with `.tar.gz` (source) and `.whl` (wheel) files.

## Installing the Built Package
Install your built package locally:
```sh
pip install dist/aprsrover-0.1.0-py3-none-any.whl
```

## Notes
- See the main README and examples for more advanced usage.
