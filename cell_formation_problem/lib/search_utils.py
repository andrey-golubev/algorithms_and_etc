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
        new_O = curr_cluster.value + new_cluster.value
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
    # TODO: merge
    return solution


# [2] local search:
#   1) Both-way movements
#       a) move cluster element (machine-part) to another cluster
def _move_elements(scheme, objective, solution):
    """Perform movement of cluster elements within a solution"""
    return solution


#   2) One-way movements
def _move(elem_id, src, dst):
    """
    Move element by id from src to dst, returning a copy of src and dst
    """
    src = deepcopy(src)
    dst = deepcopy(dst)
    src.remove(elem_id)
    dst.add(elem_id)
    return src, dst

#       a) move part to different cluster
def _find_best_fit_for_parts(scheme, clusters):
    """
    Rate parts within current solution. Find best fit clusters for each
    """
    rated_parts = []
    matrix = scheme.matrix
    for curr_id, cluster in enumerate(clusters):
        for part in cluster.parts:
            part_ratings = []
            for new_id, cluster in enumerate(clusters):
                rating = sum(matrix[m_id][part] for m_id in cluster.machines)
                part_ratings.append((rating, curr_id, new_id))
            best_rating = sorted(
                part_ratings, key=lambda x: x[0], reversed=True)[0]
            if best_rating[1] != best_rating[2]:
                # if best cluster is the one part currently in, do not count it
                rating = (part,) + best_rating
                rated_parts.append(rating)
    return sorted(rated_parts, key=lambda x: x[1])


def _move_parts(scheme, O, S):
    """Perform movement of parts between clusters within a solution"""
    clusters = construct_clusters(scheme, S)
    new_clusters = deepcopy(clusters)
    for i in range(len(clusters)):
        if clusters[i].near_empty:
            continue
        cluster_a = deepcopy(clusters[i])
        for j in range(i + 1, len(clusters)):
            if clusters[j].near_empty:
                continue
            cluster_b = deepcopy(clusters[j])
            for part in cluster_a.parts:
                cluster_a.parts, cluster_b.parts = _move(
                    part, cluster_a.parts, cluster_b.parts)
                # apply updates
                updated_clusters = deepcopy(new_clusters)
                updated_clusters[i] = cluster_a
                updated_clusters[j] = cluster_b
                new_S = Solution.from_clusters(scheme, updated_clusters)
                if satisfies_constraints(scheme, new_S):
                    if O(scheme, new_S) > O(scheme, S):
                        S = new_S
                if cluster_a.near_empty or cluster_a.near_empty:
                    break
    return S


#       b) move machine to different cluster
def _move_machines(scheme, objective, solution):
    """Perform movement of machines between clusters within a solution"""
    return solution


def local_search(scheme, objective, solution):
    """Perform local search"""
    # solution = _move_parts(scheme, objective, solution)
    return solution
