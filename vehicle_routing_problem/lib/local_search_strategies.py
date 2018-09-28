#!/usr/bin/env python3

"""
Internal library for local search strategies
"""

import unittest

# [1] 2-opt | credits: https://en.wikipedia.org/wiki/2-opt
def _two_opt_swap(route, i, k):
    """Perform 2-opt swap on route for i and k"""
    if i >= len(route) or k >= len(route):
        raise ValueError('index out of range')
    return route[:i] + list(reversed(route[i:k+1])) + route[k+1:]


def _distance(graph, route):
    """Calculate overall distance in route"""
    return sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))


def two_opt_on_route(graph, route):
    """Perform 2-opt strategy for single route"""
    # TODO: (verify that can optimize 0=>any) OR (do greedy: 0=>any and any'=>0)
    route = route[1:len(route)-1]  # remove back depot from search
    improvement = True
    while improvement:
        best_distance = _distance(graph, route)
        found_new_best = False
        for i in range(1, len(route) - 1):
            if found_new_best:  # fast loop-break
                break
            for k in range(i + 1, len(route) - 1):
                new_route = _two_opt_swap(route, i, k)
                new_distance = _distance(graph, new_route)
                if new_distance < best_distance:
                    route = new_route
                    found_new_best = True
                    break
        # if new best found: continue
        # else: stop
        improvement = found_new_best
    return [graph.depot] + route + [graph.depot]




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

    def test_two_opt_on_route_works(self):
        """Test 2-opt works for single route"""
        class Costs(object):
            def __getitem__(self, key):
                """Get cost value by key"""
                costs = {
                    (0, 1): 1,
                    (0, 2): 1,
                    (0, 3): 2,
                    (1, 2): 2,
                    (1, 4): 1,
                    (3, 2): 1,
                    (3, 4): 1,
                }
                return costs.get(tuple(sorted(key)), 3)
        class TestGraph(object):
            def __init__(self):
                """Init method"""
                self.costs = Costs()
                self.depot = 0

        test_route = [0, 1, 4, 5, 2, 3, 0]
        expected = [0, 1, 2, 5, 4, 3, 0]
        self.assertEqual(
            expected,
            two_opt_on_route(TestGraph(), test_route))

if __name__ == '__main__':
    unittest.main()
