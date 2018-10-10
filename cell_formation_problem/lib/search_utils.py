"""
Search utilities
"""
from copy import deepcopy

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
    from problem_utils import CfpObjective
    from problem_utils import Cluster
    from problem_utils import Solution
    from problem_utils import construct_clusters


def create_initial_solution(scheme):
    """Create initial solution"""
    m = scheme.machines_number
    p = scheme.parts_number
    m_clusters = [0]*m
    p_clusters = [0]*p
    return Solution(clusters=(m_clusters, p_clusters))


# [1] shake:
#  a) merge 2 bad clusters into 1
#  b) split bad cluster into 2(2+?)
def _to_elements(scheme, cluster, excludes={'m': set(), 'p': set()}):
    """Decompose cluster to elements"""
    # exclude parts and machines
    machines = deepcopy(cluster.machines)
    parts = deepcopy(cluster.parts)
    machines = machines - excludes['m']
    parts = parts - excludes['p']
    if not parts or not machines:
        return []

    machine_to_parts = {}
    for m_id in machines:
        machine_to_parts[m_id] = machine_to_parts.get(m_id, [])
        for p_id in parts:
            machine_to_parts[m_id].append(p_id)
    part_to_machines = {}
    for p_id in parts:
        part_to_machines[p_id] = part_to_machines.get(p_id, [])
        for m_id in machines:
            part_to_machines[p_id].append(m_id)
    elements = []
    matrix = scheme.matrix
    for m_id in machines:
        for p_id in parts:
            # value of element:
            # number of ones at the cross of the element in cluster
            value = 0
            value += sum(matrix[m_id][i] for i in machine_to_parts[m_id])
            value += sum(matrix[i][p_id] for i in part_to_machines[p_id])
            elements.append((m_id, p_id, value))
    return sorted(elements, key=lambda x: x[2])


def _split_in_two(scheme, cluster):
    """Detach machine-part elements from cluster and return 2 clusters"""
    base_O = CfpObjective.cluster_objective(scheme, cluster)
    new_clusters = [cluster, Cluster(scheme, 0, set(), set())]
    excludes = { 'm': set(), 'p': set() }
    elements = _to_elements(scheme, cluster, excludes=excludes)
    while elements:
        # find worst element
        # detach it from cluster
        # see if objective grows for 2 clusters
        machine_id, part_id, _ = elements.pop(0)
        excludes['m'].add(machine_id)
        excludes['p'].add(part_id)
        curr_cluster = deepcopy(new_clusters[0])
        curr_cluster.machines.remove(machine_id)
        curr_cluster.parts.remove(part_id)
        new_cluster = deepcopy(new_clusters[1])
        new_cluster.machines.add(machine_id)
        new_cluster.parts.add(part_id)
        new_O = CfpObjective.cluster_objective(scheme, curr_cluster)
        new_O += CfpObjective.cluster_objective(scheme, new_cluster)
        if new_O > base_O:
            # better objective => accept change
            new_clusters[0] = curr_cluster
            new_clusters[1] = new_cluster
            base_O = new_O
            elements = _to_elements(scheme, new_clusters[0], excludes=excludes)

    # clean-up empty clusters
    cleaned_clusters = []
    while new_clusters:
        cluster = new_clusters.pop(0)
        if not cluster.empty:
            cleaned_clusters.append(cluster)

    return cleaned_clusters


def _split(scheme, O, S):
    """Split bad clusters in solution"""
    clusters = construct_clusters(scheme, S)
    new_clusters = []
    for cluster in clusters:
        if not cluster.can_split:
            # copy "as is"
            new_clusters.append(cluster)
            continue
        new_clusters += _split_in_two(scheme, cluster)
    # fix ids:
    for i in range(len(new_clusters)):
        new_clusters[i].id = i
    new_S = Solution.from_clusters(scheme, new_clusters)
    if satisfies_constraints(scheme, new_S):
        S = new_S
    else:  # shouldn't happen
        raise ValueError('infeasible solution in split')
    return S


def shake(scheme, objective, solution):
    """Perform shaking procedure"""
    solution = _split(scheme, objective, solution)
    return solution


# [2] local search:
#  a) move part to different cluster
#  b) move machine to different cluster
def local_search(scheme, objective, solution):
    """Perform local search"""
    return solution
