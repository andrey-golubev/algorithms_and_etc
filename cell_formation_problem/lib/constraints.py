"""
Library with VNS constraints for solution
"""


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
    Check that each cluster contain at least 1 machine and  1 part
    """
    machine_clusters = set(solution['m'])
    parts_clusters = set(solution['p'])
    return machine_clusters == parts_clusters


def satisfies_constraints(scheme, solution):
    """Check that solution satisfies constraints"""
    constraints = [
        _satisfies_machines_assignments_constraint,
        _satisfies_parts_assignments_constraint,
        _satisfies_equivalence_constraint
    ]
    satisfies = True
    for constraint in constraints:
        satisfies &= constraint(scheme, solution)
    return satisfies
