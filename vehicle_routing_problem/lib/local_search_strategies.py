#!/usr/bin/env python3

"""
Internal library for local search strategies
"""

import unittest
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
    from lib.graph import Objective
    from lib.customer import Customer
    from lib.constraints import satisfies_all_constraints


# [1] 2-opt | credits: https://en.wikipedia.org/wiki/2-opt
def _two_opt_swap(route, i, k):
    """Perform 2-opt swap on route for i and k"""
    if i >= len(route) or k >= len(route):
        raise ValueError('index out of range')
    return route[:i] + list(reversed(route[i:k+1])) + route[k+1:]


def _reconstruct(graph, route):
    """Reconstruct proper route from trimmed"""
    return [graph.depot] + route + [graph.depot]


def _two_opt_on_route(graph, objective, solution, route_index, md):
    """Perform 2-opt strategy for single route"""
    # TODO: (verify that can optimize 0=>any) OR (do greedy: 0=>any and any'=>0)
    route = solution[route_index]
    route = route[1:len(route)-1]  # remove back depot from search
    can_improve = True
    while can_improve:
        curr_best_O = objective(graph, solution, md)
        found_new_best = False
        for i in range(1, len(route) - 1):
            if found_new_best:  # fast loop-break
                break
            for k in range(i + 1, len(route) - 1):
                new_route = _two_opt_swap(route, i, k)
                new_S = solution.changed(_reconstruct(graph, new_route), route_index)
                O = objective(graph, new_S, md)
                if O < curr_best_O and satisfies_all_constraints(graph, new_S):
                    route = new_route
                    found_new_best = True
                    solution = new_S
                    break
        # if new best found: continue
        # else: stop
        can_improve = found_new_best
    return _reconstruct(graph, route)


def two_opt(graph, objective, solution, md=None):
    """Perform 2-opt operation on solution"""
    routes = [None] * len(solution)
    for i in range(len(solution)):
        routes[i] = _two_opt_on_route(graph, objective, solution, i, md)
    return Solution(routes)


# [2] relocate operation
def _distance_on_route(graph, route, i, k):
    """
    Calculate distance from node (i) to node (k-1)

    Note: this is kind of a oversimplified objective function
    """
    if i < 0 or len(route) < k:
        raise ValueError('i < 0 or len(route) < k')
    return sum(graph.costs[[route[ci], route[ci+1]]] for ci in range(i, k-1))


def _is_loop(route):
    """Check whether route is a loop"""
    if len(route) > 2:
        return False
    if len(route) == 1:
        return True
    return route[0] == route[1]


def _delete_loops(solution):
    to_pop = []
    for i in range(len(solution)):
        if _is_loop(solution.routes[i]):
            to_pop.append(i)
    # delete in reverse order not to screw the indexing
    for route_index in reversed(to_pop):
        del solution.routes[route_index]
    return solution


def _relocate_one(customer, graph, objective, S, md=None):
    """Relocate single customer"""
    if customer == graph.depot:  # do not relocate depots
        return S
    ignore = False
    if md:
        ignore = md.get('ignore_feasibility', False)
    sorted_neighbours = graph.neighbours[customer]
    curr_best_O = objective(graph, S, md)
    for neighbour, dist in sorted_neighbours:
        c_route_index, c_index = S.find_route(customer)
        if c_route_index is None:
            # customer does not belong to any route. shouldn't happen
            raise IndexError('route for customer not found')
        if neighbour == graph.depot:
            # handle depot separately:
            # if there are free vehicles, create new route
            # else: skip depot -> can't relocate
            if len(S.routes) >= graph.vehicle_number:
                continue
            new_routes = copy.deepcopy(S.routes)
            new_routes.append(_reconstruct(graph, [customer]))
            new_routes[c_route_index].pop(c_index)
            new_S = Solution(new_routes)
            new_O = objective(graph, new_S, md)
            if new_O > curr_best_O:  # skip if not better
                continue
            if not satisfies_all_constraints(graph, new_S):
                continue
            return new_S
        n_route_index, n_index = S.find_route(neighbour)
        if n_route_index is None:
            # neighbour does not belong to any route. shouldn't happen
            raise IndexError('route for customer\'s neighbour not found')
        if c_route_index == n_route_index:
            # no need to relocate within a single route
            continue
        customer_route = S.routes[c_route_index]
        neighbour_route = S.routes[n_route_index]
        if _is_loop(customer_route) or _is_loop(neighbour_route):
            continue
        # TODO: use objective instead of distance
        customer_distance = _distance_on_route(
            graph,
            customer_route,
            c_index,
            c_index+2)
        customer_distance += _distance_on_route(
            graph,
            customer_route,
            c_index-1,
            c_index+1)
        dist_customer_neighbour_prev = dist + graph.costs[[customer, neighbour_route[n_index-1]]]
        dist_customer_neighbour_next = dist + graph.costs[[customer, neighbour_route[n_index+1]]]
        if customer_distance < dist_customer_neighbour_prev and customer_distance < dist_customer_neighbour_next:
            # infeasible to relocate anything
            continue
        # found better
        new_routes = copy.deepcopy(S.routes)
        if dist_customer_neighbour_prev < dist_customer_neighbour_next:
            new_routes[n_route_index].insert(n_index, customer)
        else:
            new_routes[n_route_index].insert(n_index+1, customer)
        new_routes[c_route_index].pop(c_index)
        new_S = Solution(new_routes)
        if objective(graph, new_S, md) >= curr_best_O:  # infeasible to relocate
            continue
        if ignore:
            S = new_S
        if not satisfies_all_constraints(graph, new_S):
            continue
        S = new_S
        break
    return _delete_loops(S)


def relocate(graph, objective, solution, md=None):
    """
    Perform relocate operation on solution

    Move a customer from one route to another if makes sense.
    Note: Can relocate to an "empty" route.
    """
    for customer in graph.customers:
        solution = _relocate_one(customer, graph, objective, solution, md)
    return solution


# [3] exchange operation
def exchange(graph, objective, solution, md=None):
    """
    Perform exchange operation on solution

    Swap customer visits in different vehicle routes
    """
    # noop
    return Solution(solution.routes)


# [4] cross operation
def cross(graph, objective, solution, md=None):
    """
    Perform cross operation on solution

    Swap the end portions of two vehicle routes
    """
    # noop
    return Solution(solution.routes)


# Unit Tests
def _c(id):
    """
    Create Customer object from id

    Warning: used for test purposes only
    """
    if isinstance(id, Customer):
        return id
    return Customer([id, 0, 0, 0, 0, 100, 0])


def _customerize(ids):
    """
    Create Customer list from ids list

    Warning: used for test purposes only
    """
    return [_c(id) for id in ids]


class Costs(object):
    def __init__(self, cost_function=None):
        self.calc_cost = cost_function
        if not self.calc_cost:
            self.calc_cost = Costs.default_costs

    @staticmethod
    def default_costs(key):
        key = (_c(key[0]).id, _c(key[1]).id)
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

    def __getitem__(self, key):
        """Get cost value by key"""
        return self.calc_cost(key)

class TestGraph(object):
    def __init__(self, neighbours=None, cost_function=None):
        """Init method"""
        self.costs = Costs(cost_function)
        self.depot = _c(0)
        self.neighbours = neighbours
        self.vehicle_number = 100
        self.customer_number = 0
        self.vehicle_capacity = 100


def distance(graph, solution, md):
    """Calculate overall distance"""
    del md
    s = 0
    for route in solution:
        s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
    return s


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
        # single route solutions used
        test = Solution([
            _customerize([0, 1, 4, 5, 2, 3, 0]),
            _customerize([0, 1, 2, 5, 6, 4, 3, 0])
        ])
        expected = Solution([
            _customerize([0, 1, 2, 5, 4, 3, 0]),
            _customerize([0, 1, 2, 6, 5, 4, 3, 0])
        ])
        actual = two_opt(
            TestGraph(),
            distance,
            test,
            md=None)
        self.assertEqual(expected, actual)

    def test_distance_on_route_works(self):
        """Test _distance_on_route works"""
        test = [0, 1, 4, 5, 2, 3, 0]
        size = len(test)
        self.assertEqual(13, _distance_on_route(TestGraph(), test, 0, size))
        self.assertEqual(11, _distance_on_route(TestGraph(), test, 0, size - 1))
        self.assertEqual(3, _distance_on_route(TestGraph(), test, 2, 4))
        self.assertEqual(0, _distance_on_route(TestGraph(), test, 2, 3))


class LssRelocateTests(unittest.TestCase):
    """Unit Tests for search_utils methods"""
    def _prepare_neighbours(self, cost_func):
        neighbours = {
            _c(0): [],
            _c(1): [],
            _c(2): [],
            _c(3): [],
            _c(4): [],
            _c(5): [],
            _c(6): []
        }
        for n in neighbours.keys():
            neighbours[n] = sorted(
                [(other, cost_func((n, other))) for other in neighbours.keys() if other != n],
                key=lambda x: x[1])
        return neighbours

    def test_relocate_one_works_1(self):
        """Test relocate works for single customer"""
        def relocate_costs(key):
            key = (_c(key[0]).id, _c(key[1]).id)
            costs = {
                (2, 4): 1,
                (2, 5): 2
            }
            return costs.get(tuple(sorted(key)), 3)
        neighbours = self._prepare_neighbours(relocate_costs)

        actual = Solution([
            _customerize([0, 1, 2, 3, 0]),
            _customerize([0, 4, 5, 6, 0])
        ])
        expected = Solution([
            _customerize([0, 1, 3, 0]),
            _customerize([0, 4, 2, 5, 6, 0])
        ])
        graph = TestGraph(neighbours, relocate_costs)
        actual = _relocate_one(_c(2), graph, distance, actual)
        self.assertEqual(expected, actual)

    def test_relocate_one_works_2(self):
        """Test relocate works for single customer"""
        def relocate_costs(key):
            key = (_c(key[0]).id, _c(key[1]).id)
            costs = {
                    (0, 2): 1,
                    (2, 4): 1,
                }
            return costs.get(tuple(sorted(key)), 3)
        neighbours = self._prepare_neighbours(relocate_costs)

        actual = Solution([
            _customerize([0, 1, 2, 3, 0]),
            _customerize([0, 4, 5, 6, 0])
        ])
        expected = Solution([
            _customerize([0, 1, 3, 0]),
            _customerize([0, 2, 4, 5, 6, 0])
        ])
        graph = TestGraph(neighbours, relocate_costs)
        graph.vehicle_number = 2
        actual = _relocate_one(_c(2), graph, distance, actual)
        self.assertEqual(expected, actual)

    def test_relocate_one_works_3(self):
        """
        Test relocate works for single customer

        Test relocate creates new route if possible when depot is closest
        to customer
        """
        def relocate_costs(key):
            key = (_c(key[0]).id, _c(key[1]).id)
            costs = {
                    (0, 2): 1,
                    (2, 4): 1,
                }
            return costs.get(tuple(sorted(key)), 3)
        neighbours = self._prepare_neighbours(relocate_costs)

        actual = Solution([
            _customerize([0, 1, 2, 3, 0]),
            _customerize([0, 4, 5, 6, 0])
        ])
        expected = Solution([
            _customerize([0, 1, 3, 0]),
            _customerize([0, 4, 5, 6, 0]),
            _customerize([0, 2, 0])
        ])
        graph = TestGraph(neighbours, relocate_costs)
        graph.vehicle_number = 3
        actual = _relocate_one(_c(2), graph, distance, actual)
        self.assertEqual(expected, actual)

    def test_relocate_one_works_4(self):
        """
        Test relocate works for single customer

        Test relocate does nothing if no better solution found
        """
        def relocate_costs(key):
            return 3
        neighbours = self._prepare_neighbours(relocate_costs)

        actual = Solution([
            _customerize([0, 1, 2, 3, 0]),
            _customerize([0, 4, 5, 6, 0])
        ])
        expected = Solution([
            _customerize([0, 1, 2, 3, 0]),
            _customerize([0, 4, 5, 6, 0])
        ])
        graph = TestGraph(neighbours, relocate_costs)
        actual = _relocate_one(_c(2), graph, distance, actual)
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
