"""
Library with VNS constraints for solution
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
    from problem_utils import construct_clusters


def _satisfies_machines_assignments_constraint(scheme, solution):
    """
    Check that solution satisfies: each machine has a cluster

    Note: machine belongs to 1 cluster is satisfied by solution's format
    """
    return scheme.machines_number == solution.shape[0]


def _satisfies_parts_assignments_constraint(scheme, solution):
    """
    Check that solution satisfies: each part has a cluster

    Note: part belongs to 1 cluster is satisfied by solution's format
    """
    return scheme.parts_number == solution.shape[1]


def _satisfies_equivalence_constraint(scheme, solution):
    """
    Check that each cluster contain at least 1 machine and 1 part
    """
    machine_clusters = set(solution['m'])
    parts_clusters = set(solution['p'])
    return machine_clusters == parts_clusters


def _satisfies_intersection_constraint(scheme, solution):
    """Check that any 2 different clusters do not intersect in members"""
    clusters = construct_clusters(scheme, solution)
    clusters_instersect = False
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            clusters_instersect |= bool(clusters[i].machines & clusters[j].machines)
            clusters_instersect |= bool(clusters[i].parts & clusters[j].parts)
    return not clusters_instersect


def satisfies_constraints(scheme, solution):
    """Check that solution satisfies constraints"""
    constraints = [
        _satisfies_machines_assignments_constraint,
        _satisfies_parts_assignments_constraint,
        _satisfies_equivalence_constraint,
        _satisfies_intersection_constraint
    ]
    satisfies = True
    for constraint in constraints:
        satisfies &= constraint(scheme, solution)
    return satisfies
