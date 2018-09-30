#!/usr/bin/env python3

"""
Library for local search and initial solution
"""

import unittest
import concurrent.futures as futures
import multiprocessing
import copy


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
    from lib.customer import Customer
    from lib.local_search_strategies import two_opt
    from lib.local_search_strategies import relocate
    from lib.constraints import satisfies_all_constraints
    from lib.constraints import find_capacity_violations, find_time_violations


def _greedy_initial(graph):
    """Construct initial solution greedily"""
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
    return Solution(routes=routes)


def _naive_initial(graph):
    """Construct initial solution naively"""
    routes = []
    depot = graph.depot
    non_visited_customers = {c for c in graph.customers if not c.is_depot}
    while non_visited_customers:
        customer = non_visited_customers.pop()
        # construct single customer routes. don't mind vehicle limit
        routes.append([depot, customer, depot])
    return Solution(routes=routes)


def _reconstruct(graph, route):
    if not route[0] == graph.depot:
        route.insert(0, graph.depot)
    if not route[-1] == graph.depot:
        route.append(graph.depot)
    return route


def _split_route_by_capacity(graph, route):
    """Split route into separate to fulfill constraints"""
    routes = []
    start = 0
    capacity = graph.capacity
    for i, c in enumerate(route):
        capacity -= c.demand
        if capacity < 0:
            split_route = _reconstruct(graph, route[start:i])
            routes.append(split_route)
            start = i
            capacity += graph.capacity
    if start != len(route):
        routes.append(_reconstruct(graph, route[start:len(route)]))
    return routes


def _split_route_by_time(graph, route):
    """Split route into separate to fulfill constraints"""
    routes = []
    start = 0
    time = 0
    # c.ready + c.service + distance(c, next_c) + next_c.service
    # <=
    # next_c.due_date
    for i in range(len(route)-1):
        c = route[i]
        next_c = route[i+1]
        time += c.ready_time + c.service_time + graph.costs[[c, next_c]]
        time += next_c.service_time
        if time > next_c.due_date:
            routes.append(route[start:i+1])
            start = i+1
    return routes


def _make_feasible(graph, S):
    """
    Make solution feasible

    1. Find violations
    2. Split route into separate to fulfill requirements
    """
    capacity_violations = find_capacity_violations(graph, S)
    for ri, _ in reversed(capacity_violations):
        del S.routes[ri]
    for ri, route in capacity_violations:
        routes = _split_route_by_capacity(graph, route)
        S.append(routes)

    # TODO: time violations
    # time_violations = find_time_violations(graph, S)
    # for ri, route in time_violations:
    #     routes = _split_route_by_time(graph, route)
    #     S.append(routes)
    # for ri, _ in reversed(time_violations):
    #     del S.routes[ri]
    return S


def construct_initial_solution(graph, objective, md=None):
    """
    Construct initial solution given a graph

    1. Create naive solution
    2. Use relocate to construct decent solution
    3. Make solution feasible
    """
    S = _naive_initial(graph)
    if md:
        md = copy.deepcopy(md)
        md['ignore_feasibility'] = True
    S = relocate(graph, objective, S, md)
    S = _make_feasible(graph, S)
    S = relocate(graph, objective, S, md)
    return S


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
    single_thread = True
    if single_thread:
        S_relocate = relocate(graph, objective, solution, md)
        S_two_opt = two_opt(graph, objective, solution, md)
        O_relocate = objective(graph, S_relocate, md)
        O_two_opt = objective(graph, S_two_opt, md)
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
        def distance(graph, solution, md):
            """Calculate overall distance"""
            del md
            s = 0
            for route in solution:
                s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
            return s
        self.obj = distance

    def test_construct_initial_solution_works(self):
        S = construct_initial_solution(self.graph, self.obj)
        if SearchUtilsTests.VERBOSE:
            print(S)
        self.assertTrue(S)

    def test_local_search_works(self):
        S = construct_initial_solution(self.graph, self.obj)
        S_opt = local_search(self.graph, self.obj, S, None)
        self.assertNotEqual(
            S, S_opt,
            msg='{S1} == {S2}'.format(S1=str(S), S2=str(S_opt)))
        if SearchUtilsTests.VERBOSE:
            print(S)
            print(S_opt)

    def test_split_route_works(self):
        def _c(id, demand=0, r_time=0, dd=0, s_time=0):
            return Customer([id, 0, 0, demand, r_time, dd, s_time])

        class Tmp(object):
            def __init__(self):
                self.capacity = 3
                self.depot = _c(0, 0, dd=100)
                # self.costs = lambda x: 1
        graph = Tmp()
        actual = [
            graph.depot,
            _c(1, 2),
            _c(2, 1),
            _c(3, 3),
            _c(4, 3),
            _c(5, 1),
            _c(6, 1),
            graph.depot
        ]
        expected = [
            [graph.depot, _c(1, 2), _c(2, 1), graph.depot],
            [graph.depot, _c(3, 3), graph.depot],
            [graph.depot, _c(4, 3), graph.depot],
            [graph.depot, _c(5, 1), _c(6, 1), graph.depot]
        ]
        actual = _split_route_by_capacity(graph, actual)
        self.assertEqual(expected, actual)

        # actual = [
        #     graph.depot,
        #     _c(1, 2, 10, 11, 1),
        #     _c(2, 1, 3, 10, 2),
        #     _c(3, 3, 0, 7, 1),
        #     _c(4, 3, 5, 6, 1),
        #     _c(5, 1, 0, 8, 2),
        #     _c(6, 1, 0, 16, 6),
        #     graph.depot
        # ]
        # expected = [
        #     [graph.depot, _c(5), _c(1), _c(6), graph.depot],
        #     [graph.depot, _c(2), _c(3), graph.depot],
        #     [graph.depot, _c(4), graph.depot],
        # ]
        # actual = _split_route_by_time(graph, actual)
        # self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
