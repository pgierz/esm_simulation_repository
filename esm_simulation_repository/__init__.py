# -*- coding: utf-8 -*-

"""Top-level package for ESM Simulation Repository."""

__author__ = """Paul Gierz"""
__email__ = "pgierz@awi.de"
__version__ = "0.1.0"


# Python Standard Library Imports
import logging
import os
import sys
import getpass

# Third-Party Imports
from atlassian import Confluence
import intake


def param_file_to_dict(param_file):
    logging.debug("Loading params....")
    params = {}
    with open(param_file, "r") as param_file_dat:
        for line in param_file_dat.readlines():
            line = line.strip()
            logging.debug(line)
            if line:
                try:
                    k, v = line.split(":", 1)
                except ValueError:
                    print("Couldn't split %s for for file %s" % (line, param_file))
                    raise
                v = v.replace(" ", "")
                if k not in params:
                    params[k] = [v]
                else:
                    params[k].append(v)
    # PG: Purify the list -- if you have a single element list; just add the
    # entry directly to the key.
    for k, v in params.items():
        if len(v) == 1:
            params[k] = v[0]
    return params


class SpacesExperimentTable(object):
    """
    Retrieves experiments from https://spaces.awi.de/pages/viewpage.action?pageId=290456136
    """
    def __init__(self):
        user = input("Please enter your username for spaces.awi.de: ")
        passwd = getpass.getpass("Please enter your password for spaces.awi.de: ")
        self.confluence = Confluence(url="https://spaces.awi.de", username=user, password=passwd)


class ParameterFileError(Exception):
    """Raise this error when the Parameter file has issues"""


class SimulationRepository(object):
    """
    A representation of the Simulation Repository. Tries to make
    ``RepoExperiment`` objects (or subclasses thereof) for any folder found.


    Generating this object can be configured via environmental variables. If
    the env. variable ``ESM_SIM_REPO_BASE_DIR`` is set; this is assumed to be
    the base directory. An argument passed to the object constructor superceeds
    this. The hard-coded default is ``/scratch/simulation_database/incoming/``

    The following is assumed:

    1. Every **directory** in ``base_dir`` is a simulation.
    2. Rules are applied to sort the ``base_dir`` into concrete sub-objects:
        a. If a file ``${EXPID}.parameters`` is found; the ``complexity`` in
           this file is used to determine which model is used.
        b. If no such file is found, at least ``input``, ``output``,
           ``scripts``, and ``executable`` folders must be defined.
    3. A "black-list" is applied. By default, this is an empty list. However,
       any directory listed here is excluded from the automatic sorting into
       ``RepoExperiment`` objects.
    """

    def __init__(self, base_dir=None, black_list=[]):
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.environ.get(
                "ESM_SIM_REPO_BASE_DIR", "/scratch/simulation_database/incoming/"
            )
        # Uncategorized experiments:
        self.experiments = []
        # Cosmos Experiments
        cosmos_runs = []
        logging.debug("Looking at %s" % self.base_dir)
        for folder in os.listdir(self.base_dir):
            folder = os.path.join(self.base_dir, folder)
            logging.debug("Checking for: %s", folder)
            if os.path.isdir(folder) and folder not in black_list:
                param_file = os.path.join(
                    folder, os.path.basename(folder) + ".parameters"
                )
                if os.path.isfile(param_file):
                    params = param_file_to_dict(param_file)
                    complexity = params.get("complexity")
                    if "cosmos" in complexity:
                        cosmos_run = COSMOSExperiment(base_dir=folder, params=params)
                        cosmos_runs.append(cosmos_run)
                    else:
                        # FIXME: Maybe this should just default to the general RepoExperiment?
                        raise ParameterFileError(
                            "No complexity defined for %s" % complexity
                        )
                else:
                    self.experiments.append(RepoExperiment(base_dir=folder))
        self.cosmos = COSMOSCatalog(entry_list=cosmos_runs)

    def __repr__(self):
        return f"<SimulationRepository with {len(self.experiments)} experiments>"


class RepoExperiment(intake.catalog.base.Catalog):
    def __init__(self, base_dir, **kwargs):
        self.base_dir = base_dir if not base_dir.endswith("/") else base_dir[:-1]

        self.expid = os.path.basename(self.base_dir)

        self.executable_dir = os.path.join(self.base_dir, "executable")
        self.input_dir = os.path.join(self.base_dir, "input")
        self.output_dir = os.path.join(self.base_dir, "output")
        self.scripts_dir = os.path.join(self.base_dir, "scripts")

        super(RepoExperiment, self).__init__(**kwargs)


class COSMOSExperiment(RepoExperiment):
    def __init__(self, params=None, *args, **kwargs):
        super(COSMOSExperiment, self).__init__(*args, **kwargs)

        self.params = params or param_file_to_dict(
            os.path.join(self.base_dir, self.expid + ".parameters")
        )
        self.original_output_dir = self.params["output"].copy()
        self._entries = {}
        for file_tag in [
            "echam5_main_mm",
            "echam5_wiso_mm",
            "echam5_co2_mm",
            "jsbach_veg_mm",
            "jsbach_land_mm",
            "jsbach_main_mm",
            "jsbach_surf_mm",
        ]:
            flist = [
                os.path.join(self.output_dir, os.path.basename(f))
                for f in self.params["output"]
                if self.expid + "_" + file_tag in f
            ]
            logging.debug(f"Setting up: {file_tag}")
            self._entries[file_tag] = intake.catalog.local.LocalCatalogEntry(
                name=file_tag.replace("_mm", ""),
                description=f"{file_tag.replace('_mm', '').replace('_', ' ')} files",
                driver="netcdf",
                direct_access=True,
                args={
                    "urlpath": flist,
                    "xarray_kwargs": {
                        "decode_times": False,
                        "combine": "nested",
                        "parallel": True,
                    },
                },
            )

    def __repr__(self):
        return "<COSMOSExperiment expid=%s, base_dir=%s>" % (self.expid, self.base_dir)


class COSMOSCatalog(intake.catalog.base.Catalog):
    def __init__(self, name=None, description=None, entry_list=None, *args, **kwargs):
        super(COSMOSCatalog, self).__init__(*args, **kwargs)
        entry_list = entry_list or []
        name = name or "cosmos_exps"
        description = (
            description
            or "COSMOS Experiments in the AWI Paleoclimate Dynamics Repository"
        )
        self._entries = {}
        for entry in entry_list:
            name = entry.expid
            description = f"Comos Experiment {name}"
            metadata = entry.params

            # self._entries[name] = intake.catalog.local.LocalCatalogEntry(
            #    name=name, description=description, metadata=metadata, driver="catalog",
            # )
            self._entries[name] = entry
