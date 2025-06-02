from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

with open(here / "README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="aprsrover",
    version="0.1.0",
    description="Python library for APRS Rover utilities: APRS messaging, GPS, and rover track control.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="5B4AON",
    license="MIT",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "gpsd-py3",
        "Adafruit-PCA9685",
        "kiss3",
        "ax253"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries"
    ],
    include_package_data=True,
)
