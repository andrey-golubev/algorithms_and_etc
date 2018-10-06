import argparse

# local imports
from contextlib import contextmanager
@contextmanager
def import_from(rel_path):
    """Add module import relative path to sys.path"""
    import sys
    import os
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(cur_dir, rel_path))
    yield
    sys.path.pop(0)

with import_from('.'):
    from lib.search_utils import local_search_methods


def basic_parser():
    """Return basic parser for command-line arguments"""
    parser = argparse.ArgumentParser("")
    parser.add_argument('instances',
        nargs='+',
        help='Vehicle Routing Problem instance file(s)')
    parser.add_argument('--max-iter',
        help='Iterated Local Search max iterations',
        type=int,
        default=2000)
    parser.add_argument('--no-sol',
        action='store_true',
        help='Specifies, whether solution files needs to be generated')
    parser.add_argument('--time-limit',
        help='Algorithm time limit (in seconds)',
        type=int,
        default=60*60)
    parser.add_argument('--exclude-ls',
        help='Exclude specific local search (LS) heuristics',
        nargs='*',
        choices=local_search_methods().keys(),
        default=[])
    return parser
