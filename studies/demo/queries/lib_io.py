"""Provides support to read/manipulate yaml files"""

import pathlib
import enum
import yaml
from typing import Optional, Union, List, Tuple



class YAMLExtensions(enum.Enum):
    """Defines (valid) YAML file extensions"""
    VALIDext = 'yml', 'yaml'
    OTHERext = None

    @classmethod
    def _missing_(cls, file_name_or_extension: str):
        """
        This method allows:
        - mapping VALIDext to multiple extentions
        - passing full path to file as input
        """
        if (file_name_or_extension in cls.VALIDext.value or
                pathlib.Path(file_name_or_extension).suffix[1:] in cls.VALIDext.value):
            return cls(cls.VALIDext.value)
        return cls(None)


class SQLExtensions(enum.Enum):
    """Defines (valid) YAML file extensions"""
    VALIDext = 'sql'
    OTHERext = None

    @classmethod
    def _missing_(cls, file_name_or_extension: str):
        """
        This method allows:
        - mapping VALIDext to multiple extentions
        - passing full path to file as input
        """
        if (file_name_or_extension in cls.VALIDext.value or
                pathlib.Path(file_name_or_extension).suffix[1:] in cls.VALIDext.value):
            return cls(cls.VALIDext.value)
        return cls(None)


def read_yaml(path_to_file: str) -> dict:
    """
    Reads content of yaml file into dictionary. Error is raised if file etension is not recognised.
    """

    if YAMLExtensions(path_to_file) == YAMLExtensions.VALIDext:
        return yaml.safe_load(open(path_to_file, 'r'))
    raise ValueError(f'{path_to_file} is not a YAML')


def read_sql(path_to_file: str) -> dict:
    """
    Reads content of sql file into a string. Error is raised if file etension is not recognised.
    """

    if SQLExtensions(path_to_file) == SQLExtensions.VALIDext:

        with open(path_to_file, 'r') as fp:
            lines = fp.readlines()
        return "".join(lines)
    raise ValueError(f'{path_to_file} is not a SQL')


def read_from_dir(
    path_to_dir: str,
    extension: str, 
    on_error_continue: Optional[bool] = False,
    max_depth: Optional[int] = 3
) -> Union[dict, Tuple[dict, List[str]]]:
    """Load all (and only) YAML files in folder, including nested directories up to a specified depth.
    The method can be generalised to load any extensions.

    Args:
        path_to_dir (str): Path to folder/yaml file
        extension (str): Extension to read.
        on_error_continue (Optional[bool], optional): If True, it will not raise error if a file with 
            yaml extension fails to load. Defaults to False.
        max_depth (Optional[int], optional): List of (yaml) file names which failed loading. Only 
            returned if `on_error_continue=True`. Defaults to 3.

    Raises:
        YAMLExtensions error.
        SQLExtensions error. 

    Returns:
        collection (dict): dictionary with (possibly nested) dictionaries.
        failed_yaml (list of str): name of files which could not be loaded.
    """

    # define file format to be read
    if YAMLExtensions(extension) == YAMLExtensions.VALIDext:
        CURRENTextension = YAMLExtensions
        read_file = read_yaml
    elif SQLExtensions(extension) == SQLExtensions.VALIDext:
        CURRENTextension = SQLExtensions
        read_file = read_sql
    else:
        ValueError(f"Extension {extension} not supported!")


    # if path_to_dir is a directory, loop through its items
    collection, failed_yaml = {}, []

    for file_or_dir in pathlib.Path(path_to_dir).iterdir():
        f_path = str(file_or_dir.absolute())

        # if sub-directory: read only if maximum depth not reached
        if file_or_dir.is_dir() and max_depth > 0:
            new_item, failed_here = read_from_dir(
                f_path, extension, on_error_continue,  max_depth-1)
            failed_yaml += failed_here

        # if YAML, try to read
        elif CURRENTextension(f_path) == CURRENTextension.VALIDext:
            try:
                new_item = read_file(f_path)
            except Exception as err:
                if on_error_continue:
                    failed_yaml.append(f_path)
                    continue
                raise err

        # else ignore file
        else:
            continue

        # If sub-directory/file contain something, store
        if bool(new_item):
            collection[file_or_dir.stem] = new_item

    return collection, failed_yaml

