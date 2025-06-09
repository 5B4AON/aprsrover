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
python3 -m build
```
This will create a `dist/` directory with `.tar.gz` (source) and `.whl` (wheel) files.

## Installing the Built Package
Install your built package locally:
```sh
pip install dist/aprsrover-0.1.0-py3-none-any.whl
```

## Uploading to PyPi
So that others can install via `pip install aprsrover`ppyt
```sh
python3 -m twine upload dist/*
```
