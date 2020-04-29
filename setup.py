#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=6.0",
]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest",
]

setup(
    name="esm_simulation_repository",
    version="0.1.0",
    description="An Intake driver for simulations created with ESM-Tools",
    long_description=readme + "\n\n" + history,
    author="Paul Gierz",
    author_email="pgierz@awi.de",
    url="https://github.com/pgierz/esm_simulation_repository",
    packages=find_packages(include=["esm_simulation_repository"]),
    entry_points={"console_scripts": ["sim_repo=esm_simulation_repository.cli:main"]},
    package_dir={"esm_simulation_repository": "esm_simulation_repository"},
    include_package_data=True,
    install_requires=requirements,
    license="GNU General Public License v3",
    zip_safe=False,
    keywords="esm_simulation_repository",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    test_suite="tests",
    tests_require=test_requirements,
    setup_requires=setup_requirements,
)
