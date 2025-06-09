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
So that others can install via `pip install aprsrover`  
Install tools  
```sh
python3 -m pip install --upgrade twine
```  
 
- Go to TestPyPI account settings
- Click on "Add API token"
- Give your token a name (e.g., "twine upload") and, if you want, restrict it to a specific project
- Click "Add token" and copy the token (it starts with pypi-...)
- Create a file called .pypirc in your home directory (not your project directory):
    ```
    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = __token__
    password = pypi-<your-token-here>
    ```
Upload to TestPyPi
```sh
python3 -m twine upload --repository testpypi dist/*
``` 

Install from TestPyPi
```sh
pip install -i https://test.pypi.org/simple/aprsrover
```  

Upload to PyPi  
```sh
python3 -m twine upload dist/*
```
Install from PyPi
```sh
pip install aprsrover
```  