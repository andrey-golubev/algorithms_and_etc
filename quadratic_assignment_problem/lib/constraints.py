"""
Library with GA constraints for solution
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


def _satisfies_length_constraint(problem, solution):
    """Check that solution's length is always N"""
    return len(solution) == problem.n


def _satisfies_assignment_constraint(problem, solution):
    """Check that each facility is assigned to a unique (only one) location"""
    return len(solution) == len(set(l for l in solution))


def satisfies_constraints(problem, solution):
    """Check that solution satisfies constraints"""
    constraints = [
        _satisfies_length_constraint,
        _satisfies_assignment_constraint
    ]
    satisfies = True
    for constraint in constraints:
        satisfies &= constraint(problem, solution)
    return satisfies
