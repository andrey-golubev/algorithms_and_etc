#!/usr/bin/env python3

import argparse
import os
import sys
import time
import progressbar
import math
import random
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

with import_from('.'):
    from lib.graph import Graph
    from lib.graph import Objective
    from lib.graph import PenaltyMap
    import lib.search_utils as search
    from lib.visualize import visualize
    from lib.constraints import satisfies_all_constraints
    from lib.generate_output import generate_sol


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("")
    parser.add_argument('instances',
        nargs='+',
        help='Vehicle Routing Problem instance file(s)')
    parser.add_argument('--max-iter',
        help='Iterated Local Search max iterations',
        default=2000)
    parser.add_argument('--swap-factor',
        help='A swap factor for perturbation',
        default=0.4)
    parser.add_argument('--no-sol',
        action='store_true',
        help='Specifies, whether solution files needs to be generated')
    return parser.parse_args()


class IlsObjective(Objective):
    """Iterated local search objective function"""
    def _distance(self, graph, solution):
        """Calculate overall distance"""
        s = 0
        for route in solution:
            s += sum(graph.costs[(route[i], route[i+1])] for i in range(len(route)-1))
        return s

    def _route_distance(self, graph, route):
        """Calculate route distance"""
        return sum(graph.costs[(route[i], route[i+1])] for i in range(len(route)-1))

    def __call__(self, graph, solution, md):
        """operator() overload"""
        if md and md['ri']:
            return self._route_distance(graph, solution[md['ri']])
        return self._distance(graph, solution)


def _sort_solution_by_objective(graph, O, S, history):
    """Sort routes by impact on objective function in descending order"""
    return sorted([ri for ri in range(len(S)) if ri not in history],
        key=lambda x: O(graph, S, {'ri': x}), reverse=True)


def swap_nodes(route_a, route_b, ci_a, ci_b):
    """
    Swap node indexed ci_a with node indexed ci_b between corresponding routes

    Note: this function *does not* swap in-place
    """
    a = copy.deepcopy(route_a)
    b = copy.deepcopy(route_b)
    tmp_c = copy.deepcopy(a[ci_a])
    a[ci_a] = copy.deepcopy(b[ci_b])
    b[ci_b] = tmp_c
    return a, b


def _perturbation(graph, O, S, md):
    """Perform perturbation on solution"""
    # TODO: a good one is a 4-opt between routes
    random.seed(a=11)
    # history = md['history']
    # number of swaps to perform
    swaps = int(md['swap_factor'] * random.randint(2, len(S) - 1))
    swaps = max(swaps, 1)

    # TODO: sort doesn't seem necessary
    # indices = _sort_solution_by_objective(graph, O, S, history)
    indices = [ri for ri in range(len(S))]  # if ri not in history]
    if len(indices) < 2:
        # can't perform at least one swap
        return S

    random.shuffle(indices)  # shuffle to get random order
    # perform as many swaps as possible
    swaps = int(min(swaps, math.floor(len(indices) / 2)))
    while indices and swaps:
        # perform any swap operation between 2 routes
        ri = indices.pop(0)
        route = S[ri]
        for i in range(len(indices)):
            if not swaps:
                break
            next_ri = indices[i]
            next_route = S[next_ri]
            for ci in range(len(route)):
                if route[ci] == graph.depot:
                    continue
                if ci in md['history']:
                    continue
                if not swaps:
                    break
                for next_ci in range(len(next_route)):
                    if next_route[next_ci] == graph.depot:
                        continue
                    if next_ci in md['history']:
                        continue
                    # move = random.uniform(0, 1) >= 0.5
                    # if not move:
                        # continue
                    new_route, new_next_route = swap_nodes(
                        route, next_route, ci, next_ci)
                    new_S = S.changed(new_route, ri)
                    new_S = new_S.changed(new_next_route, next_ri)
                    satisfies = satisfies_all_constraints(graph, new_S)
                    if not satisfies:
                        continue
                    S = new_S
                    swaps -= 1
                    md['history'].add(ci)
                    md['history'].add(next_ci)
                    break
    return S


def iterated_local_search(graph, factor, max_iter):
    """Iterated local search algorithm"""
    # O - objective function
    # S - current solution
    # best_S <=> S*
    # MD - method specific supplementary data

    # some progressbar to show how method is doing
    # progress = progressbar.ProgressBar(
    #     maxval=max_iter,
    #     widgets=[
    #         progressbar.Bar('=', '[', ']'),
    #         ' ',
    #         progressbar.Percentage()])

    O = IlsObjective()
    MD = {
        'ignore_feasibility': False,
        'history': set(),  # history of perturbation: swapped customers
        # 'iter': max_iter * 0.05,  # number of iterations in perturbation
        'swap_factor': factor  # swap paratemeter for perturbation
    }
    S = search.construct_initial_solution(graph, O, MD)
    if not satisfies_all_constraints(graph, S):
        raise ValueError("couldn't find satisfying initial solution")
    best_S = S

    if VERBOSE:
        print('O = {o}'.format(o=O(graph, S, None)))
        # progress.start()

    for i in range(max_iter):
        # if VERBOSE:
            # progress.update(i+1)
        S = _perturbation(graph, O, S, MD)
        S = search.local_search(graph, O, S, None)

        if VERBOSE and i % 10 == 0:
            print("O* so far:", O(graph, best_S, None))

        if S == best_S:
            # solution didn't change after perturbation + local search
            break
        # MD['history'] = set()
        if O(graph, S, None) >= O(graph, best_S, None):
            continue
        best_S = S

    # if VERBOSE:
        # progress.finish()

    # final LS with no penalties to get true local min
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
        S = iterated_local_search(graph, args.swap_factor, args.max_iter)
        elapsed = time.time() - start
        if VERBOSE:
            print('O* = {o}'.format(o=IlsObjective()(graph, S, None)))
            print('All served?', S.all_served(graph.customer_number))
            print('Everything satisfied?', satisfies_all_constraints(graph, S))
            print('----- PERFORMANCE -----')
            print('GLS took {some} seconds'.format(some=elapsed))
            print('-'*100)
            # visualize(S)
        if not args.no_sol:
            filedir = os.path.dirname(os.path.abspath(__file__))
            generate_sol(graph, S, cwd=filedir, prefix='_ils_')
    return 0


if __name__ == '__main__':
    VERBOSE = True
    sys.exit(main())
