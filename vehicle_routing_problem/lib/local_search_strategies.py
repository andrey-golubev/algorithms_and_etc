#!/usr/bin/env python3

"""
Internal library for local search strategies
"""

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
    from lib.graph_utils import Objective


# [1] 2-opt | credits: https://en.wikipedia.org/wiki/2-opt
def _two_opt_swap(route, i, k):
    """Perform 2-opt swap on route for i and k"""
    if i >= len(route) or k >= len(route):
        raise ValueError('index out of range')
    return route[:i] + list(reversed(route[i:k+1])) + route[k+1:]


def _reconstruct(graph, route):
    """Reconstruct proper route from trimmed"""
    return [graph.depot] + route + [graph.depot]


def _two_opt_on_route(graph, objective, solution, route_index, penalties):
    """Perform 2-opt strategy for single route"""
    # TODO: (verify that can optimize 0=>any) OR (do greedy: 0=>any and any'=>0)
    route = solution[route_index]
    route = route[1:len(route)-1]  # remove back depot from search
    can_improve = True
    while can_improve:
        curr_best_O = objective(graph, solution, penalties)
        found_new_best = False
        for i in range(1, len(route) - 1):
            if found_new_best:  # fast loop-break
                break
            for k in range(i + 1, len(route) - 1):
                new_route = _two_opt_swap(route, i, k)
                O = objective(
                    graph,
                    solution.changed(_reconstruct(graph, new_route), route_index),
                    penalties)
                if O < curr_best_O:
                    route = new_route
                    found_new_best = True
                    solution = solution.changed(
                        _reconstruct(graph, new_route),
                        route_index)
                    break
        # if new best found: continue
        # else: stop
        can_improve = found_new_best
    return _reconstruct(graph, route)


def two_opt(graph, objective, solution, penalties=None):
    """Perform 2-opt operation on solution"""
    routes = [None] * len(solution)
    for i in range(len(solution)):
        routes[i] = _two_opt_on_route(graph, objective, solution, i, penalties)
    return Solution(routes)



# Unit Tests
class LssTests(unittest.TestCase):
    """Unit Tests for search_utils methods"""
    def test_two_opt_swap_works_basic_case(self):
        """Test 2-opt swap works"""
        test_route = ['A', 'D', 'B', 'C']
        expected = ['A', 'B', 'D', 'C']
        self.assertEqual(
            expected,
            _two_opt_swap(test_route, 1, 2))

    def test_two_opt_swap_works_nodes_between(self):
        """Test 2-opt swap works when nodes are between"""
        test_route = ['A', 'D', 'X', 'E', 'B', 'C']
        expected = ['A', 'B', 'E', 'X', 'D', 'C']
        self.assertEqual(
            expected,
            _two_opt_swap(test_route, 1, 4))

    def test_two_opt_works(self):
        """Test 2-opt works"""
        class Costs(object):
            def __getitem__(self, key):
                """Get cost value by key"""
                costs = {
                    (0, 1): 1,
                    (0, 2): 1,
                    (0, 3): 2,
                    (1, 2): 2,
                    (1, 4): 1,
                    (2, 6): 1,
                    (3, 2): 1,
                    (3, 4): 1,
                    (5, 6): 1,
                }
                return costs.get(tuple(sorted(key)), 3)
        class TestGraph(object):
            def __init__(self):
                """Init method"""
                self.costs = Costs()
                self.depot = 0

        def distance(graph, solution, penalties):
            """Calculate overall distance"""
            del penalties
            s = 0
            for route in solution:
                s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
            return s

        # single route solutions used
        test = Solution([
            [0, 1, 4, 5, 2, 3, 0],
            [0, 1, 2, 5, 6, 4, 3, 0]
        ])
        expected = Solution([
            [0, 1, 2, 5, 4, 3, 0],
            [0, 1, 2, 6, 5, 4, 3, 0]
        ])
        actual = two_opt(
            TestGraph(),
            distance,
            test,
            penalties=None)
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
