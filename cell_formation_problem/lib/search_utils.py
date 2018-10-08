"""
Search utilities
"""

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
    from problem_utils import Solution


def create_initial_solution(scheme):
    """Create initial solution"""
    m = scheme.machines_number
    p = scheme.parts_number
    m_clusters = [i for i in range(m)]
    p_clusters = [i for i in range(p)]
    return Solution(clusters=(m_clusters, p_clusters))


def shake(scheme, objective, solution):
    """Perform shaking procedure"""
    return solution


def local_search(scheme, objective, solution):
    """Perform local search"""
    return solution
