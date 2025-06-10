"""
Tools to help use queries across experiments/notebooks and test them.
"""

import pathlib
import jinja2
from . import lib_io

_QUERIES_FOLDER = str(pathlib.Path(__file__).parent)
queries, _ = lib_io.read_from_dir( _QUERIES_FOLDER, extension='sql')


def render_model( query: str, jinja_params: dict = {}):
    """Renders a model query with jinja parameters/syntax.

    Args:
        query (str): query to render - supports Jinja syntax.
        jinja_params (dict, optional): Jinja parameters in model. Defaults to {}.
    """

    query_sql = jinja2.Template(query).render(**jinja_params)
    return query_sql

print(f"[DEBUG] All available queries are: {queries.keys()}")