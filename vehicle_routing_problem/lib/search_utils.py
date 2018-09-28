#!/usr/bin/env python3

"""
Library for local search and initial solution
"""

# 1) initial solution
# 2) 2-opt
# 3) ? relocation
# 4) tests
# input: vector of paths
# output: new vector of paths
# can do optional: (found, new vector of paths)

import unittest

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
    from lib.graph_utils import Solution
    from lib.local_search_strategies import two_opt_on_route


def construct_initial_solution(graph, ignore_constraints=False):
    """Construct Initial Solution given a GraphUtils object"""
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
                next_customer = graph.costs[i]
                visited.add(next_customer)
                vehicle_route.append(next_customer)
                route_capacity -= demand
            non_visited_customers -= visited
        vehicle_route.append(depot)
        routes.append(vehicle_route)

    if not ignore_constraints:
        if len(routes) > graph.vehicle_number:
            raise ValueError('initial solution error: vehicle number exceeded')
        # TODO: additional constraints
    return Solution(routes=routes)


def local_search(graph, solution):
    """Perform local search"""
    def two_opt(graph, solution):
        """Perform 2-opt operation on solution"""
        routes = [None] * len(solution)
        for i, route in enumerate(solution):
            routes[i] = two_opt_on_route(graph, route)
        return Solution(routes)
    # TODO: implement "smarter" local search
    return two_opt(graph, solution)


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
        from graph_utils import GraphUtils
        from io import StringIO
        self.graph = GraphUtils(StringIO(SearchUtilsTests.BASIC_VRP))
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
        try:
            S = construct_initial_solution(self.graph, ignore_constraints=False)
            S_opt = local_search(self.graph, S)
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
