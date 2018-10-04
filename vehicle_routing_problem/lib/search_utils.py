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
    from lib.local_search_strategies import exchange
    from lib.constraints import satisfies_all_constraints
    from lib.constraints import route_satisfies_constraints
    from lib.constraints import find_capacity_violations, find_time_violations


def _reconstruct(graph, route):
    if not route:
        raise ValueError('empty route')
    if not route[0] == graph.depot:
        route.insert(0, graph.depot)
    if not route[-1] == graph.depot:
        route.append(graph.depot)
    return route


# initial solution
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


def _unfulfilled_demands(graph, non_visited_customers):
    """
    Return unfulfilled customers and their demands in descending order
    """
    return sorted(
        [c for c in graph.customers if c in non_visited_customers],
        key=lambda c: c.demand,
        reverse=True)


def _average_capacity_initial(graph):
    """Construct initial solution maintaining average capacity per route"""
    avg_cap = graph.avg_capacity
    routes = []
    non_visited_customers = {c for c in graph.customers if not c.is_depot}
    for _ in range(graph.vehicle_number):
        if not non_visited_customers:
            break
        vehicle_route = []  # current route
        route_cap = float(graph.capacity)  # current route capacity
        route_fulfilled_cap = float(0)
        non_wanted_customers = set()  # all not wanted in current iteration
        while non_visited_customers and route_fulfilled_cap < avg_cap:
            visited = set()  # visited customers so far
            if non_wanted_customers == non_visited_customers:
                # cannot add anyone: finish current iteration
                break
            demands = _unfulfilled_demands(graph, non_visited_customers)
            if demands and route_cap < demands[-1].demand:
                break
            while demands:  # if there's anyone to add
                next_customer = demands.pop(0)
                demand = next_customer.demand
                if demand > route_cap:  # violates capacity constraint
                    continue
                new_route = copy.deepcopy(vehicle_route)
                new_route.append(next_customer)
                satisfies = route_satisfies_constraints(
                    graph, _reconstruct(graph, new_route))
                if not satisfies and route_fulfilled_cap < avg_cap:
                    # if constraints violated and route does not fulfill
                    # average capacity, "reconsider" route nodes
                    # => remove last customer and find better fit
                    cancelled_customer = vehicle_route.pop()
                    non_wanted_customers.add(cancelled_customer)
                    route_cap += cancelled_customer.demand
                if satisfies:
                    # add new customer to current route
                    visited.add(next_customer)
                    vehicle_route.append(next_customer)
                    route_cap -= demand
                    route_fulfilled_cap += demand
            non_visited_customers -= visited
        # add not wanted back to not visited
        non_visited_customers |= non_wanted_customers
        # construct new route
        routes.append(_reconstruct(graph, vehicle_route))
    return Solution(routes=routes)


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
        time += c.ready_time + c.service_time + graph.costs[(c, next_c)]
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


def _INTERNAL_construct_initial_solution(graph, objective, md=None):
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
    # S = relocate(graph, objective, S, md)
    return S


def construct_initial_solution(graph, objective, md=None):
    """Construct initial solution given a graph"""
    return _average_capacity_initial(graph)


# local search
def _methods():
    """Return available methods used in local search"""
    return {
        '2-opt': two_opt,
        'relocate': relocate,
        'exchange': exchange
    }


def _do_method(method, graph, O, S, md=None):
    S = method(graph, O, S, md)
    return (O(graph, S, md), S)


def local_search(graph, objective, solution, md=None):
    """Perform local search"""
    single_thread = False
    methods = _methods()
    results = []
    if single_thread:
        for method in methods.values():
            S = method(graph, objective, solution, md)
            results.append((objective(graph, S, md), S))
    else:
        with futures.ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
            future_per_search_method = {executor.submit(_do_method, m, graph, objective, solution, md): name for name, m in methods.items()}
            for future in futures.as_completed(future_per_search_method):
                results.append(future.result())
        if not results:
            raise Exception('Every method failed')
    # get solution that gives best objective
    return sorted(results, key=lambda x: x[0])[0][1]



# Unit Tests
class SearchUtilsTests(unittest.TestCase):
    """Unit Tests for search_utils methods"""

    BASIC_VRP = """
C108_shortened_x10

VEHICLE
NUMBER     CAPACITY
5         50

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
                s += sum(graph.costs[(route[i], route[i+1])] for i in range(len(route)-1))
            return s
        self.obj = distance

    def test_construct_initial_solution_works(self):
        S = construct_initial_solution(self.graph, self.obj)
        if SearchUtilsTests.VERBOSE:
            print(S)
        self.assertTrue(S.routes)
        self.assertTrue(S.all_served(self.graph.customer_number))

    def test_local_search_works(self):
        S = construct_initial_solution(self.graph, self.obj)
        S_opt = local_search(self.graph, self.obj, S, None)
        self.assertTrue(S.routes)
        self.assertTrue(S_opt.all_served(self.graph.customer_number))
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
