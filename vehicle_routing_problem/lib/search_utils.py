#!/usr/bin/env python3

"""
Library for local search and initial solution
"""

import unittest
import concurrent.futures as futures
import multiprocessing


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


with import_from('../'):
    from lib.graph import Solution
    from lib.graph import Graph
    from lib.local_search_strategies import two_opt
    from lib.local_search_strategies import relocate
    from lib.constraints import satisfies_all_constraints


def construct_initial_solution(graph, ignore_constraints=False):
    """Construct Initial Solution given a Graph object"""
    routes = []
    depot = graph.depot
    # TODO: optimize whole operation
    non_visited_customers = {c for c in graph.customers if not c.is_depot}
    for _ in range(graph.vehicle_number):
        if not non_visited_customers:
            break
        if len(routes) == graph.vehicle_number:
            break
        vehicle_route = [depot]
        route_capacity = float(graph.capacity)
        unfulfilled_demands = sorted(
            [(c.id, c.demand) for c in graph.customers if c in non_visited_customers],
            key=lambda x: x[1],
            reverse=True)
        while non_visited_customers and (route_capacity >= unfulfilled_demands[-1][1]):
            visited = set()
            for i, demand in unfulfilled_demands:
                if demand > route_capacity:
                    continue
                updated_route = vehicle_route
                updated_routes = routes
                next_customer = graph.costs[i]
                updated_route.append(next_customer)
                updated_route.append(depot)
                updated_routes.append(updated_route)
                if not satisfies_all_constraints(graph, Solution(updated_routes)):
                    break
                visited.add(next_customer)
                vehicle_route = updated_route[:len(updated_route) - 1]
                route_capacity -= demand
            non_visited_customers -= visited
        vehicle_route.append(depot)
        routes.append(vehicle_route)

    if not ignore_constraints:
        if len(routes) > graph.vehicle_number:
            raise ValueError('initial solution error: vehicle number exceeded')
        # TODO: additional constraints
    return Solution(routes=routes)


def _methods():
    """Return available methods used in local search"""
    return {
        '2-opt': two_opt,
        'relocate': relocate
    }


def _do_method(method, graph, O, S, md=None):
    S = method(graph, O, S, md)
    return (O(graph, S, md), S)


def local_search(graph, objective, solution, md=None):
    """Perform local search"""
    single_thread = False
    if single_thread:
        S_relocate = relocate(graph, objective, solution, md)
        S_two_opt = two_opt(graph, objective, solution, md)
        O_two_opt = objective(graph, S_two_opt, md)
        O_relocate = objective(graph, S_relocate, md)
        # slightly prefer relocate over 2-opt
        return S_relocate if O_relocate <= O_two_opt else S_two_opt
    else:
        methods = _methods()
        results = []
        with futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            future_per_search_method = {executor.submit(_do_method, m, graph, objective, solution, md): name for name, m in methods.items()}
            for future in futures.as_completed(future_per_search_method):
                results.append(future.result())
        if not results:
            raise Exception('Every method failed')
        return sorted(results, key=lambda x: x[0])[0][1]


def choose_penalty_features(graph, solution, md):
    """Choose features to penalize upon given a solution"""
    edges = []
    for route in solution:
        for i in range(len(route)-1):
            edges.append((route[i], route[i+1]))
    return edges




# Unit Tests
class SearchUtilsTests(unittest.TestCase):
    """Unit Tests for search_utils methods"""

    BASIC_VRP = """
C108_shortened_x10

VEHICLE
NUMBER     CAPACITY
3         50

CUSTOMER
CUST NO.   XCOORD.   YCOORD.   DEMAND    READY TIME   DUE DATE   SERVICE TIME

    0      40         50          0          0       1236          0
    1      45         68         10        830       1049         90
    2      45         70         30        756        939         90
    3      42         66         10         16        336         90
    4      42         68         10        643        866         90
    5      42         65         10         15        226         90
    6      40         69         20        499        824         90
    7      40         66         20         87        308         90
    8      38         68         20        150        429         90
    9      38         70         10        429        710         90
"""

    VERBOSE = False

    def setUp(self):
        from io import StringIO
        self.graph = Graph(StringIO(SearchUtilsTests.BASIC_VRP))
        super(SearchUtilsTests, self).setUp()

    def test_construct_initial_solution_works(self):
        try:
            S = construct_initial_solution(self.graph, ignore_constraints=False)
            if SearchUtilsTests.VERBOSE:
                print(S)
            self.assertTrue(S)
        except Exception as e:
            self.fail(str(e))

    def test_local_search_works(self):
        def distance(graph, solution, md):
            """Calculate overall distance"""
            del md
            s = 0
            for route in solution:
                s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
            return s
        try:
            S = construct_initial_solution(self.graph, ignore_constraints=False)
            S_opt = local_search(self.graph, distance, S, None)
            self.assertNotEqual(
                S, S_opt,
                msg='{S1} == {S2}'.format(S1=str(S), S2=str(S_opt)))
            if SearchUtilsTests.VERBOSE:
                print(S)
                print(S_opt)
        except Exception as e:
            self.fail(str(e))


if __name__ == '__main__':
    unittest.main()
