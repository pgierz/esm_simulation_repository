# -*- coding: utf-8 -*-

"""Top-level package for ESM Simulation Repository."""

__author__ = """Paul Gierz"""
__email__ = "pgierz@awi.de"
__version__ = "0.1.0"


# Python Standard Library Imports
import io
import logging
import os

# Third-Party Imports
import intake

ESM_SIM_REPO_BASE_DIR = "/scratch/simulation_database/incoming/"
"""
str : The default simulation repository base directory that is used when
constructing an SimulationRepository object.
"""


def param_file_to_dict(param_file):
    """
    Turns a parameter file (C. Stepanek's standard) into a dictionary.

    Christian Stepanek has introduced a ``${EXPID}.parameters`` file to keep
    track of what is in the simulation repository. This file includes important
    information regarding the simulation configuration, original file paths,
    and binaries. This function turns this file into a dictionary, and more
    generally, can transform any file which contains a list of ``key: value``
    items into a dictionary.

    The following rules are applied:

    * Each line in the file must have a ``":"``
    * Left is the key, and, if present, right is the value. If there is no
      value, it should result in a ``None`` value. Otherwise, right is a
      ``str`` or ``list of str``
    * If a key appears more than once, the value for that key is transformed to
      a list, and the order of values for that list conform to the top-down order
      in the file.

    Parameters
    ----------
    param_file : str or filelike
        The file to parse

    Returns
    -------
    dict :
        The dictionary representation of the file as described above.

    Raises
    ------
    ParameterFileError :
        Raised if the split between ``key: value`` does not work correctly.

    TypeError :
        Raised if you don't give a string or an object with ``readlines``.
    """
    logging.debug("Loading params....")
    params = {}
    if isinstance(param_file, str):
        with open(param_file, "r") as param_file_dat:
            lines = param_file_dat.readlines()
    elif isinstance(param_file, io.IOBase):
        lines = param_file.readlines()
    else:
        raise TypeError("Argument ``'param_file'`` must be ``str`` or ``File``")
    for line in lines:
        line = line.strip()
        logging.debug(line)
        if line:
            try:
                k, v = line.split(":", 1)
            except ValueError:
                raise ParameterFileError(
                    "Couldn't split %s for for file %s" % (line, param_file)
                )
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


class ParameterFileError(Exception):
    """Raise this error if the Parameter file has something unexpected"""


class SimulationRepository(object):
    """
    A representation of the Simulation Repository. Tries to make
    ``RepoExperiment`` objects (or subclasses thereof) for any folder found.


    Generating this object can be configured via environmental variables. If
    the env. variable ``ESM_SIM_REPO_BASE_DIR`` is set; this is assumed to be
    the base directory. An argument passed to the object constructor superceeds
    this. The hard-coded default is taken from the module constants.

    The following is assumed:

    1. Every **directory** in ``base_dir`` is a simulation.

    2. Rules are applied to sort the ``base_dir`` into concrete sub-objects:

        a. If a file ``${EXPID}.parameters`` is found; the ``complexity`` in
           this file is used to determine which model is used.

        b. If no such file is found, at least ``input``, ``output``,
           ``scripts``, and ``executable`` folders must be defined.

    3. A "black-list" is applied. By default, this is an empty list. However,
       any directory listed here is excluded from the automatic sorting into
       ``RepoExperiment`` objects. It can also be passed in via the
       environmental variable ESM_SIM_REPO_BLACK_LIST as a colon seperated list
       of experiment IDs.
    """

    def __init__(self, base_dir=None, black_list=None):
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.environ.get(
                "ESM_SIM_REPO_BASE_DIR", ESM_SIM_REPO_BASE_DIR
            )
        if black_list is None:
            env_black_list = os.environ.get("ESM_SIM_REPO_BLACK_LIST", "")
            env_black_list = env_black_list.split(":")
            black_list = [item for item in env_black_list if item]
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
    def __init__(self, base_dir, expid=None, **kwargs):
        """
        A representation of an experiment in the simulation repository.

        Initialization requires the ``base_dir`` argument, which should point
        to the top-level folder in the repository with this experiment's files.

        The following attributes are assigned:

        ``expid`` : The experiment ID is assumed to be the basename of the
        ``base_dir`` argument. It can be over-ridden by passing
        ``expid=<something>`` during object creation.

        Currently, the following folders are automatically added as strings:

        * ``executable_dir`` : Binaries for the various model components are
          copied here

        * ``input_dir`` : Any files required for model initialization are
          copied here

        * ``output_dir`` : Simulation results (normally **not** divided by
          subfolders) are placed here.

        * ``scripts_dir`` : Simulation scripts (typically run and post scripts)
          are copied here.

        After these attributes are set, the initialization routine of the base
        class (``intake.catalog.base.Catalog``) is run.

        Parameters
        ----------

        base_dir : str
            The base directory for this particular experiment *in the
            simulation repository*. Note that this should **not** be the
            original base directory from the computing cluster!

        expid : str
            The experiment ID of this simulation, e.g. ``conpi``. Defaults to
            ``None``, in which case it is extracted from the ``base_dir`` as
            the basename.
        """
        self.base_dir = base_dir if not base_dir.endswith("/") else base_dir[:-1]

        self.expid = expid or os.path.basename(self.base_dir)

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
        return f"<COSMOSExperiment expid={self.expid}, base_dir={self.base_dir}>"


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
            self._entries[name] = entry
