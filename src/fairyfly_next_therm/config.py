"""Fairyfly-Next THERM configurations.

Import this into every module where access configurations are needed.

Usage:

.. code-block:: python

    from fairyfly_next_therm.config import folders
    print(folders.lbnl_data_path)
    folders.lbnl_data_path = "C:/Users/Person/LBNL"
"""
import os
import json
import pkgutil

import ladybug.config as lb_config


class Folders(object):
    """Fairyfly-Next THERM folders.

    Args:
        config_file: The path to the config.json file from which folders are loaded.
            If None, the config.json module included in this package will be used.
            Default: None.
        mute: If False, the paths to the various folders will be printed as they
            are found. If True, no printing will occur upon initialization of this
            class. Default: True.

    Properties:
        * therm_path
        * therm_exe
        * therm_version
        * therm_version_str
        * fortran_dll_path
        * lbnl_data_path
        * therm_settings_path
        * therm_lib_path
        * material_lib_file
        * gas_lib_file
        * bc_steady_state_lib_file
        * user_material_folder
        * user_gas_folder
        * user_steady_state_folder
        * config_file
        * mute
    """
    THERM_VERSION = (8, 1, 30, 0)
    LBNL_URL = 'https://windows.lbl.gov/therm-software-downloads'
    FORTRAN_URL = 'https://windows.lbl.gov/redistributable-packages'

    def __init__(self, config_file=None, mute=True):
        self.mute = bool(mute)  # set the mute value
        self.config_file = config_file  # load paths from the config JSON file

    @property
    def therm_path(self):
        """Get or set the path to Therm installation folder.

        This is typically the folder within the lbnl program files directory
        that starts with THERM and contains executables and dlls.
        """
        return self._therm_path

    @therm_path.setter
    def therm_path(self, t_path):
        exe_name = 'THERM{}.exe'.format(self.THERM_VERSION[0])
        if not t_path:  # check the default installation location
            t_path = self._find_therm_folder()
        therm_exe_file = os.path.join(t_path, exe_name) if t_path is not None else None

        # if the executable exists, set the variables
        if t_path and os.path.isfile(therm_exe_file):
            self._therm_path = t_path
            self._therm_exe = therm_exe_file
            self._therm_version = self.THERM_VERSION
            self._therm_version_str = '.'.join(str(i) for i in self.THERM_VERSION)
            if not self.mute:
                print("Path to Therm is set to: %s" % self._therm_path)
        else:
            if t_path is not None and os.path.isdir(t_path):
                self._therm_path = t_path
            else:
                if t_path is not None:
                    msg = '{} is not a valid path to a Therm installation.'.format(t_path)
                    print(msg)
                self._therm_path = None
            self._therm_exe = None
            self._therm_version = None
            self._therm_version_str = None

    @property
    def therm_exe(self):
        """Get the path to Therm executable.

        Will be none if no Therm installation was found.
        """
        return self._therm_exe

    @property
    def therm_version(self):
        """Get a tuple for the version of therm (eg. (8, 1, 30)).

        This will be None if the version could not be sensed or if no Therm
        installation was found.
        """
        return self._therm_version

    @property
    def therm_version_str(self):
        """Get text for the full version of therm (eg."8.1.30").

        This will be None if the version could not be sensed or if no Therm
        installation was found.
        """
        return self._therm_version_str

    @property
    def fortran_dll_path(self):
        """Get or set the path to the directory with DLLs for FORTRAN runtime routines.

        This is typically a folder within the Shared Libraries folder of
        the common Intel files under Program Files (x86).
        """
        return self._fortran_dll_path

    @fortran_dll_path.setter
    def fortran_dll_path(self, f_path):
        if not f_path:  # check the default installation location
            f_path = self._find_fortran_dll()

        # if the executable exists, set the variables
        if f_path and os.path.isdir(f_path):
            self._fortran_dll_path = f_path
            if not self.mute:
                print("Path to Fortran DLL is set to: %s" % self._fortran_dll_path)
        else:
            self._fortran_dll_path = None

    @property
    def lbnl_data_path(self):
        """Get or set the path to the folder containing the LBNL data.

        This folder typically exists under the User profile and contains sub-folders
        for all installed versions of LBNL THERM and WINDOW. The THERM sub-folder
        contains a lib sub-folder with XML files for all materials, boundary
        conditions, etc.
        """
        return self._lbnl_data_path

    @lbnl_data_path.setter
    def lbnl_data_path(self, path):
        if not path:  # check the default locations of the template library
            path = self._find_lbnl_data_folder()

        # gather all of the sub folders underneath the master folder
        if path and os.path.isdir(path):
            self._lbnl_data_path = path
            self._therm_settings_path = self._check_therm_settings(path)
            self._material_lib_file = self._check_therm_lib_file(path, 'Materials.xml')
            self._gas_lib_file = self._check_therm_lib_file(path, 'Gases.xml')
            self._bc_steady_state_lib_file = self._check_therm_lib_file(
                path, 'BoundaryConditionsSteadyState.xml')
            if not self.mute:
                print('Path to LBNL data is set to: {}'.format(self._lbnl_data_path))
        else:
            if path:
                msg = '{} is not a valid path to a LBNL data folder.'.format(path)
                print(msg)
            self._lbnl_data_path = None
            self._therm_settings_path = None
            self._material_lib_file = None
            self._gas_lib_file = None
            self._bc_steady_state_lib_file = None

    @property
    def therm_settings_path(self):
        """Get the path to the .ini file with THERM settings.

        Will be None if no LBNL data folder was found.
        """
        return self._therm_settings_path

    @property
    def therm_lib_path(self):
        """Get or set the path to the folder from which therm materials are loaded.

        This will be the therm folder within within the user's standards folder
        if it exists.
        """
        return self._therm_lib_path

    @therm_lib_path.setter
    def therm_lib_path(self, path):
        if not path:  # check the default locations of the template library
            path = self._find_therm_lib()

        # gather all of the sub folders underneath the master folder
        if path and os.path.isdir(path):
            self._therm_lib_path = path
            mat_dir = os.path.join(path, 'materials')
            gas_dir = os.path.join(path, 'gases')
            bc_dir = os.path.join(path, 'conditions')
            self._user_material_folder = mat_dir if os.path.isdir(mat_dir) else None
            self._user_gas_folder = gas_dir if os.path.isdir(gas_dir) else None
            self._user_steady_state_folder = bc_dir if os.path.isdir(bc_dir) else None
            if not self.mute:
                print('Path to THERM library is set to: {}'.format(self._lbnl_data_path))
        else:
            if path:
                msg = '{} is not a valid path to a THERM standards library.'.format(path)
                print(msg)
            self._therm_lib_path = None
            self._user_material_folder = None
            self._user_gas_folder = None
            self._user_steady_state_folder = None

    @property
    def material_lib_file(self):
        """Get the path to the material library file."""
        return self._material_lib_file

    @property
    def gas_lib_file(self):
        """Get the path to the gas library file."""
        return self._gas_lib_file

    @property
    def bc_steady_state_lib_file(self):
        """Get the path to the steady state condition library file."""
        return self._bc_steady_state_lib_file

    @property
    def user_material_folder(self):
        """Get the path to the user material library folder."""
        return self._user_material_folder

    @property
    def user_gas_folder(self):
        """Get the path to the user gas library folder."""
        return self._user_gas_folder

    @property
    def user_steady_state_folder(self):
        """Get the path to the user steady state condition library folder."""
        return self._user_steady_state_folder

    @property
    def config_file(self):
        """Get or set the path to the config.json file from which folders are loaded.

        Setting this to None will result in using the config.json module included
        in this package.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, cfg):
        if cfg is None:
            cfg = os.path.join(os.path.dirname(__file__), 'config.json')
        self._load_from_file(cfg)
        self._config_file = cfg

    def check_therm_version(self):
        """Raise an exception message about the THERM installation if it is not usable."""
        # first, check that we are on the correct operating system
        if os.name != 'nt':
            msg = 'LBNL THERM can only run on Windows machines and so it cannot ' \
                'be used while on "{}" operating system.'.format(os.name)
            raise ValueError(msg)
        # then, check that THERM is installed and it is the correct version
        ver_str = '.'.join(str(i) for i in self.THERM_VERSION)
        dn_msg = 'Download and install THERM version {} from:\n{}'.format(
            ver_str, self.LBNL_URL)
        if self.therm_exe is not None:
            # make sure that the FORTRAN DLL library was installed
            if self.fortran_dll_path is None:
                msg = 'A valid THERM installation was found at "{}"\n' \
                    'but it does not have the required redistributable packages.\n' \
                    'To install these packages, follow the instructions at:\n ' \
                    '{}'.format(self.therm_path, self.FORTRAN_URL)
                raise ValueError(msg)
            return None  # everything is good
        elif self.therm_path is not None:
            msg = 'A THERM installation was found at "{}" but it is not ' \
                'for version {}.\nFairyfly is currently only compatible with ' \
                'this version of THERM.\n{}.'.format(self.therm_path, ver_str, dn_msg)
            raise ValueError(msg)
        else:
            msg = 'No THERM installation was found on this machine.\n{}'.format(dn_msg)
            raise ValueError(msg)

    def _load_from_file(self, file_path):
        """Set all of the the properties of this object from a config JSON file.

        Args:
            file_path: Path to a JSON file containing the file paths. A sample of this
                JSON is the config.json file within this package.
        """
        # check the default file path
        assert os.path.isfile(str(file_path)), \
            ValueError('No file found at {}'.format(file_path))

        # set the default paths to be all blank
        default_path = {
            "therm_path": r'',
            "fortran_dll_path": r'',
            "lbnl_data_path": r'',
            "therm_lib_path": r''
        }

        with open(file_path, 'r') as cfg:
            try:
                paths = json.load(cfg)
            except Exception as e:
                print('Failed to load paths from {}.\n{}'.format(file_path, e))
            else:
                for key, p in paths.items():
                    if not key.startswith('__') and p.strip():
                        default_path[key] = p.strip()

        # set paths for therm installations
        self.therm_path = default_path["therm_path"]
        self.fortran_dll_path = default_path["fortran_dll_path"]
        self.lbnl_data_path = default_path["lbnl_data_path"]
        self.therm_lib_path = default_path["therm_lib_path"]

    @staticmethod
    def _find_therm_folder():
        """Find the Therm installation in its default location."""
        # first check if there's a version installed in the ladybug_tools folder
        # note that this option is not likely to be used because of the THERM license
        lb_install = lb_config.folders.ladybug_tools_folder
        thm_path = None
        if os.path.isdir(lb_install):
            test_path = os.path.join(lb_install, 'THERM')
            thm_path = test_path if os.path.isdir(test_path) else None

        def getversion(therm_path):
            """Get digits for the version of Version."""
            try:
                ver = ''.join(s for s in therm_path if (s.isdigit() or s == '.'))
                return sum(int(d) * (10 ** i)
                           for i, d in enumerate(reversed(ver.split('.'))))
            except ValueError:  # folder starting with 'THERM' and no version
                return 0

        # then check for the default location where standalone Therm is installed
        if thm_path is None and os.name == 'nt':  # search the C:/ drive on Windows
            major, minor, _, _ = Folders.THERM_VERSION
            lbnl_install_dir = 'C:/Program Files (x86)/lbnl'
            test_path = '{}/THERM{}.{}'.format(lbnl_install_dir, major, minor)
            if os.path.isdir(test_path):
                thm_path = test_path
            elif os.path.isdir(lbnl_install_dir):
                therm_folders = []
                for f in os.listdir(lbnl_install_dir):
                    f_path = os.path.join(lbnl_install_dir, f)
                    if f.lower().startswith('therm') and os.path.isdir(f_path):
                        therm_folders.append(f_path)
                if len(therm_folders) != 0:
                    thm_path = sorted(therm_folders, key=getversion, reverse=True)[0]

        return thm_path

    @staticmethod
    def _find_fortran_dll():
        """Find the folder to the Fortran DLLs in its default location."""
        # check for the default location in Program Files (x86)
        if os.name == 'nt':  # search the C:/ drive on Windows
            dll_dir = 'C:/Program Files (x86)/Common Files/Intel/Shared Libraries/ia32'
            if os.path.isdir(dll_dir):
                return dll_dir

    @staticmethod
    def _find_lbnl_data_folder():
        """Find the LBNL data folder in its default location."""
        # then check the default location where the LBNL installer puts it
        lib_folder = None
        if os.name == 'nt':  # search the C:/ drive on Windows
            test_path = 'C:/Users/Public/LBNL/'
            if os.path.isdir(test_path):
                lib_folder = test_path
        return lib_folder

    @staticmethod
    def _check_therm_settings(path):
        """Check that a settings file exists within the LBNL data folder."""
        if not path:  # first check that a path exists
            return None
        major, minor, _, _ = Folders.THERM_VERSION
        settings_dir = os.path.join(path, 'Settings')
        set_file = os.path.join(settings_dir, 'therm{}.{}.ini'.format(major, minor))
        if os.path.isfile(set_file):
            return set_file

    @staticmethod
    def _find_therm_lib():
        """Find the user standards folder in its default location."""
        # first check if there's a user-defined folder in AppData
        app_folder = os.getenv('APPDATA')
        if app_folder is not None:
            lib_folder = os.path.join(app_folder, 'ladybug_tools', 'standards', 'therm')
            if os.path.isdir(lib_folder):
                return lib_folder
        # then check next to the Python library
        for finder, name, ispkg in pkgutil.iter_modules():
            if name == 'fairyfly_therm_standards':
                lib_folder = os.path.join(finder.path, name)
                if os.path.isdir(lib_folder):
                    return lib_folder

    @staticmethod
    def _check_therm_lib_file(path, lib_file):
        """Check that a XML file exists within the LBNL therm library."""
        if not path:  # first check that a path exists
            return None
        if os.name == 'nt':
            major, minor, _, _ = Folders.THERM_VERSION
            lib_path = os.path.join(path, 'THERM{}.{}/lib'.format(major, minor), lib_file)
            if os.path.isfile(lib_path):
                return lib_path


"""Object possesing all key folders within the configuration."""
folders = Folders(mute=True)
