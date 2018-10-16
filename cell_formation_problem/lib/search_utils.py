"""
Search utilities
"""
import concurrent.futures as futures
import multiprocessing
from copy import deepcopy
from collections import namedtuple
from itertools import permutations


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


# initial solution
def create_initial_solution(scheme):
    """Create initial solution"""
    m = scheme.machines_number
    p = scheme.parts_number
    m_clusters = [0]*m
    p_clusters = [0]*p
    return Solution(clusters=(m_clusters, p_clusters))


# parallel execution
def _execute(pipeline, scheme, O, S):
    """Caller for the sequence of methods"""
    for method in pipeline:
        S = method(scheme, O, S)
    return (O(scheme, S), S)


def _choose_best_sln(pipelines, scheme, objective, solution, single_thread=False):
    """
    Execute sequential pipelines in parallel and choose best solution

    Note: if single_thread is True, the execution in not parallel but a
    single-threaded for-loop is used instead
    """
    single_thread = False
    results = []
    if single_thread:
        for pipeline in pipelines:
            value, S = _execute(pipeline, scheme, objective, solution)
            results.append((value, S))
    else:
        with futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            futures_per_pipeline = {executor.submit(_execute, p, scheme, objective, solution) for p in pipelines}
            for future in futures_per_pipeline:
                results.append(future.result())
    if not results:
        raise RuntimeError('no pipelines executed')
    # return solution that gives best objective
    return sorted(results, key=lambda x: x[0], reverse=True)[0][1]


# [1] shake:
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


#  a) split bad cluster into 2
# TODO: split in K, where K is the best partition
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


#  b) merge bad clusters into 1
def _merge(scheme, O, S):
    """Merge bad clusters into 1"""
    clusters = construct_clusters(scheme, S)
    new_clusters = []
    while clusters:
        updated_cluster = clusters.pop(0)
        cluster_length = len(clusters)
        for _ in range(cluster_length):
            if not clusters:
                break
            next_cluster = clusters.pop(0)
            merged = deepcopy(updated_cluster)
            merged.merge(next_cluster)
            # if merged cluster is worse than split clusters, do not merge
            # else, merge
            if merged.value <= updated_cluster.value + next_cluster.value:
                clusters.append(next_cluster)
            else:
                updated_cluster = merged
        new_clusters.append(updated_cluster)
    # fix ids
    for i in range(len(new_clusters)):
        new_clusters[i].id = i
    new_S = Solution.from_clusters(scheme, new_clusters)
    if satisfies_constraints(scheme, new_S):
        S = new_S
    else:  # shouldn't happen
        raise ValueError('infeasible solution in split')
    return S


SHAKE_PIPELINES = [[_split], [_merge]]
def shake(scheme, objective, solution):
    """Perform shaking procedure"""
    return _choose_best_sln(SHAKE_PIPELINES, scheme, objective, solution)


# [2] local search:
#   1) Two-way movements
#       a) move cluster element (machine-part) to another cluster
def _find_best_fit_for_elements(scheme, clusters):
    """
    Rate elements in current solution. Find best fit cluster for each part
    """
    ElementRating = namedtuple('ElementRating',
        ['machine', 'part', 'rating', 'curr_cluster', 'new_cluster'])
    rated_elements = []
    matrix = scheme.matrix
    for curr_id, cluster in enumerate(clusters):
        if cluster.near_empty:  # can't move parts out of almost empty cluster
            continue
        parts = cluster.parts
        machines = cluster.machines
        for machine in machines:
            for part in parts:
                element_ratings = []
                for new_id, new_cluster in enumerate(clusters):
                    rating = sum(matrix[machine][p_id] for p_id in new_cluster.parts)
                    rating += sum(matrix[m_id][part] for m_id in new_cluster.machines)
                    element_ratings.append(
                        ElementRating(machine, part, rating, curr_id, new_id))
                best_rating = sorted(
                    element_ratings, key=lambda x: x.rating, reverse=True)[0]
                if best_rating.curr_cluster == best_rating.new_cluster:
                    # skip parts that are "good" in current cluster
                    continue
                rated_elements.append(best_rating)
    return sorted(rated_elements, key=lambda x: x.rating, reverse=True)


def _move_elements(scheme, O, S):
    """
    Perform movement of elements (machine-part) between clusters within a solution
    """
    clusters = construct_clusters(scheme, S)
    rated_elements = _find_best_fit_for_elements(scheme, clusters)
    while rated_elements:
        stat = rated_elements.pop(0)
        curr_id, new_id = stat.curr_cluster, stat.new_cluster
        if clusters[curr_id].near_empty:
            # can't move anything out of near empty cluster
            continue
        curr_cluster = deepcopy(clusters[curr_id])
        new_cluster = deepcopy(clusters[new_id])
        curr_cluster.machines, new_cluster.machines = _move(
            stat.machine, curr_cluster.machines, new_cluster.machines)
        curr_cluster.parts, new_cluster.parts = _move(
            stat.part, curr_cluster.parts, new_cluster.parts)
        old_value = clusters[curr_id].value + clusters[new_id].value
        new_value = curr_cluster.value + new_cluster.value
        # if new clusters have better objective than old ones, approve move
        if new_value > old_value:
            clusters[curr_id] = curr_cluster
            clusters[new_id] = new_cluster
            rated_elements = _find_best_fit_for_elements(scheme, clusters)

    # construct new S
    # if new S is better and satisfies constraints, approve changes
    new_S = Solution.from_clusters(scheme, clusters)
    if O(scheme, new_S) > O(scheme, S) and satisfies_constraints(scheme, new_S):
        S = new_S
    return S


#   2) One-way movements
def _move(element, src, dst):
    """
    Move element from src to dst, returning a copy of src and dst
    """
    src = deepcopy(src)
    dst = deepcopy(dst)
    src.remove(element)
    dst.add(element)
    return src, dst


#       a) move part to different cluster
def _find_best_fit_for_parts(scheme, clusters):
    """
    Rate parts in current solution. Find best fit cluster for each part
    """
    PartRating = namedtuple('PartRating',
        ['part', 'rating', 'curr_cluster', 'new_cluster'])
    rated_parts = []
    matrix = scheme.matrix
    for curr_id, cluster in enumerate(clusters):
        if cluster.near_empty:  # can't move parts out of almost empty cluster
            continue
        parts = cluster.parts
        for part in parts:
            part_ratings = []
            for new_id, new_cluster in enumerate(clusters):
                rating = sum(matrix[m_id][part] for m_id in new_cluster.machines)
                part_ratings.append(PartRating(part, rating, curr_id, new_id))
            best_rating = sorted(
                part_ratings, key=lambda x: x.rating, reverse=True)[0]
            if best_rating.curr_cluster == best_rating.new_cluster:
                # skip parts that are "good" in current cluster
                continue
            rated_parts.append(best_rating)
    return sorted(rated_parts, key=lambda x: x.rating, reverse=True)


def _move_parts(scheme, O, S):
    """Perform movement of parts between clusters within a solution"""
    clusters = construct_clusters(scheme, S)
    rated_parts = _find_best_fit_for_parts(scheme, clusters)
    while rated_parts:
        stat = rated_parts.pop(0)
        curr_id, new_id = stat.curr_cluster, stat.new_cluster
        if clusters[curr_id].near_empty:
            # can't move anything out of near empty cluster
            continue
        curr_cluster = deepcopy(clusters[curr_id])
        new_cluster = deepcopy(clusters[new_id])
        curr_cluster.parts, new_cluster.parts = _move(
            stat.part, curr_cluster.parts, new_cluster.parts)
        old_value = clusters[curr_id].value + clusters[new_id].value
        new_value = curr_cluster.value + new_cluster.value
        # if new clusters have better objective than old ones, approve move
        if new_value > old_value:
            clusters[curr_id] = curr_cluster
            clusters[new_id] = new_cluster
            rated_parts = _find_best_fit_for_parts(scheme, clusters)

    # construct new S
    # if new S is better and satisfies constraints, approve changes
    new_S = Solution.from_clusters(scheme, clusters)
    if O(scheme, new_S) > O(scheme, S) and satisfies_constraints(scheme, new_S):
        S = new_S
    return S


#       b) move machine to different cluster
def _find_best_fit_for_machines(scheme, clusters):
    """
    Rate machines in current solution. Find best fit cluster for each machine
    """
    MachineRating = namedtuple('MachineRating',
        ['machine', 'rating', 'curr_cluster', 'new_cluster'])
    rated_machines = []
    matrix = scheme.matrix
    for curr_id, cluster in enumerate(clusters):
        if cluster.near_empty:  # can't move machines out of almost empty cluster
            continue
        machines = cluster.machines
        for machine in machines:
            machine_ratings = []
            for new_id, new_cluster in enumerate(clusters):
                rating = sum(matrix[machine][p_id] for p_id in new_cluster.parts)
                machine_ratings.append(MachineRating(machine, rating, curr_id, new_id))
            best_rating = sorted(
                machine_ratings, key=lambda x: x.rating, reverse=True)[0]
            if best_rating.curr_cluster == best_rating.new_cluster:
                # skip machines that are "good" in current cluster
                continue
            rated_machines.append(best_rating)
    return sorted(rated_machines, key=lambda x: x.rating, reverse=True)


def _move_machines(scheme, O, S):
    """Perform movement of machines between clusters within a solution"""
    clusters = construct_clusters(scheme, S)
    rated_machines = _find_best_fit_for_machines(scheme, clusters)
    while rated_machines:
        stat = rated_machines.pop(0)
        curr_id, new_id = stat.curr_cluster, stat.new_cluster
        if clusters[curr_id].near_empty:
            # can't move anything out of near empty cluster
            continue
        curr_cluster = deepcopy(clusters[curr_id])
        new_cluster = deepcopy(clusters[new_id])
        curr_cluster.machines, new_cluster.machines = _move(
            stat.machine, curr_cluster.machines, new_cluster.machines)
        old_value = clusters[curr_id].value + clusters[new_id].value
        new_value = curr_cluster.value + new_cluster.value
        # if new clusters have better objective than old ones, approve move
        if new_value > old_value:
            clusters[curr_id] = curr_cluster
            clusters[new_id] = new_cluster
            rated_machines = _find_best_fit_for_machines(scheme, clusters)

    # construct new S
    # if new S is better and satisfies constraints, approve changes
    new_S = Solution.from_clusters(scheme, clusters)
    if O(scheme, new_S) > O(scheme, S) and satisfies_constraints(scheme, new_S):
        S = new_S
    return S


# local search
LS_PIPELINES = [p for p in permutations([
    _move_parts,
    _move_machines,
    # _move_elements
])]
def local_search(scheme, objective, solution):
    """Perform local search"""
    return _choose_best_sln(LS_PIPELINES, scheme, objective, solution)
