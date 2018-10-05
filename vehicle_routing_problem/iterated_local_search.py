#!/usr/bin/env python3

import argparse
import os
import sys
import time
import progressbar
import math
import copy
import time

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
    from lib.graph import Graph
    from lib.graph import Objective
    from lib.graph import PenaltyMap
    import lib.search_utils as search
    from lib.visualize import visualize
    from lib.constraints import satisfies_all_constraints
    from lib.generate_output import generate_sol
    from lib.local_search_strategies import swap_nodes


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("")
    parser.add_argument('instances',
        nargs='+',
        help='Vehicle Routing Problem instance file(s)')
    parser.add_argument('--max-iter',
        help='Iterated Local Search max iterations',
        type=int,
        default=2000)
    parser.add_argument('--no-sol',
        action='store_true',
        help='Specifies, whether solution files needs to be generated')
    parser.add_argument('--time-limit',
        help='Algorithm time limit (in seconds)',
        type=int,
        default=60*60)
    return parser.parse_args()


class IlsObjective(Objective):
    """Iterated local search objective function"""
    def __call__(self, graph, solution, md):
        """operator() overload"""
        if md and md.get('ri', None) is not None:
            return self._route_distance(graph, solution[md['ri']])
        return self._distance(graph, solution)


def _sort_solution_by_objective(graph, O, S):
    """Sort routes by impact on objective function in descending order"""
    return sorted([ri for ri in range(len(S))],
        key=lambda x: O(graph, S, {'ri': x}), reverse=True)


def _make_history_tuple(i, j, r, k):
    return tuple(sorted([i, j, r, k]))


def _perturbation(graph, O, S, md):
    """Perform perturbation between routes on solution"""
    # sort by highest objective
    # as O -> min, maximal values are bad
    # we need to try to reduce max values / compensate
    # this way LS can be guided towards a better solution
    routes = _sort_solution_by_objective(graph, O, S)
    four_opt_performed = False
    while not four_opt_performed and routes:
        ri_a = routes.pop(0)
        route_a = S[ri_a]
        for i in range(len(routes)):
            if four_opt_performed:
                break
            ri_b = routes[i]
            route_b = S[ri_b]
            for ci_a in range(len(route_a) - 1):
                if four_opt_performed:
                    break
                # skip depots
                if route_a[ci_a] == graph.depot:
                    continue
                if route_a[ci_a + 1] == graph.depot:
                    break
                for ci_b in range(len(route_b) - 1):
                    # skip depots
                    if route_b[ci_b] == graph.depot:
                        continue
                    if route_b[ci_b + 1] == graph.depot:
                        break
                    if _make_history_tuple(ci_a, ci_a + 1, ci_b, ci_b + 1) in md['history']:
                        # skip already swapped customers
                        continue
                    # reverse swap two customers from each route
                    new_route_a, new_route_b = swap_nodes(
                        route_a, route_b, ci_a, ci_b + 1)
                    new_route_a, new_route_b = swap_nodes(
                        new_route_a, new_route_b, ci_a + 1, ci_b)
                    new_S = S.changed(new_route_a, ri_a)
                    new_S = new_S.changed(new_route_b, ri_b)
                    satisfies = satisfies_all_constraints(graph, new_S)
                    if not satisfies:
                        continue
                    S = new_S
                    four_opt_performed = True
                    # add current tuple of 4 customers to history
                    md['history'].add(
                        _make_history_tuple(ci_a, ci_a + 1, ci_b, ci_b + 1))
                    break
    return S


def iterated_local_search(graph, max_iter, time_limit):
    """Iterated local search algorithm"""
    # O - objective function
    # S - current solution
    # best_S <=> S*
    # MD - method specific supplementary data
    best_S = None
    try:
        O = IlsObjective()
        MD = {
            'ignore_feasibility': False,
            'history': set(),  # history of perturbation: swapped customers
        }
        start = time.time()
        S = search.construct_initial_solution(graph, O, MD)
        if not satisfies_all_constraints(graph, S):
            raise ValueError("couldn't find satisfying initial solution")
        best_S = S

        if VERBOSE:
            print('O = {o}'.format(o=O(graph, S, None)))

        objective_unchanged = 0

        for i in range(max_iter):
            S = _perturbation(graph, O, S, MD)
            S = search.local_search(graph, O, S, None)

            if VERBOSE and i % max_iter / 10 == 0:
                print("O* so far:", O(graph, best_S, None))

            if S == best_S:
                # solution didn't change after perturbation + local search
                break
            if objective_unchanged > max_iter * 0.1:
                # if 10% of iterations in a row there's no improvement, stop
                break
            if O(graph, S, None) >= O(graph, best_S, None):
                objective_unchanged += 1
                continue
            objective_unchanged = 0
            best_S = S

        elapsed = time.time() - start  # in seconds
        if elapsed > time_limit:  # > 45 minutes
            print('- Timeout reached -')
            raise TimeoutError('algorithm timeout reached')
    except TimeoutError:
        pass  # supress timeout errors, expecting only from algo timeout
    finally:
        # final LS just in case
        return search.local_search(graph, O, best_S, None)


def main():
    """Main entry point"""
    args = parse_args()
    if VERBOSE:
        print(args.instances)
    for instance in args.instances:
        graph = None
        with open(instance, 'r') as instance_file:
            graph = Graph(instance_file)
            graph.name = os.path.splitext(os.path.basename(instance))[0]
        if VERBOSE:
            print('-'*100)
            print('File: {name}.txt'.format(name=graph.name))
        start = time.time()
        S = iterated_local_search(graph, args.max_iter, args.time_limit)
        elapsed = time.time() - start
        if VERBOSE:
            print('O* = {o}'.format(o=IlsObjective()(graph, S, None)))
            print('All served?', S.all_served(graph.customer_number))
            print('Everything satisfied?', satisfies_all_constraints(graph, S))
            print('----- PERFORMANCE -----')
            print('ILS took {some} seconds'.format(some=elapsed))
            print('-'*100)
            # visualize(S)
        if not args.no_sol:
            filedir = os.path.dirname(os.path.abspath(__file__))
            generate_sol(graph, S, cwd=filedir, prefix='_ils_')
    return 0


if __name__ == '__main__':
    VERBOSE = True
    sys.exit(main())
