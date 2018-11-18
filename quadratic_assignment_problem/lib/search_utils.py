"""
Search utilities
"""
import concurrent.futures as futures
import multiprocessing
from copy import deepcopy
from collections import namedtuple
from itertools import permutations
import random


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
    from constraints import satisfies_constraints
    from problem_utils import QfpObjective
    from problem_utils import Solution


# initial solution
def create_initial_solution(problem):
    """Create initial solution"""
    return Solution([i for i in range(problem.n)])
