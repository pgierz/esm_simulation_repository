#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `esm_simulation_repository` package."""
import os

import pytest

from click.testing import CliRunner

from esm_simulation_repository import cli
from esm_simulation_repository import (
    param_file_to_dict,
    ParameterFileError,
    SimulationRepository,
)

# TODO(PG) Fixup later:
import esm_simulation_repository


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/michaelaye/cookiecutter-pypackage-conda')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


def test_param_file_to_dict():
    test_file = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "conpi.parameters"
    )
    param_file_to_dict(test_file)
    with pytest.raises(ParameterFileError):
        test_file += "_bad"
        param_file_to_dict(test_file)


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "esm_simulation_repository.cli.main" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help  Show this message and exit." in help_result.output


class TestSimulationRepo:
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_init(self, monkeypatch):
        monkeypatch.setattr(
            esm_simulation_repository, "ESM_SIM_REPO_BASE_DIR", "/dev/null"
        )
        SimulationRepository()
