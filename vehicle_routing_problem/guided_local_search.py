#!/usr/bin/env python3

import argparse
import os
import sys
import time
import progressbar
import math

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
        help='Guided Local Search max iterations',
        default=2000)
    parser.add_argument('--penalty-factor',
        help='A penalty factor in objective function (works: 0.1, 0.2, 0.3)',
        default=0.2)
    parser.add_argument('--no-sol',
        action='store_true',
        help='Specifies, whether solution files needs to be generated')
    return parser.parse_args()


class GlsObjective(Objective):
    """Guided local search objective function"""
    def __call__(self, graph, solution, md):
        """operator() overload"""
        value = self._distance(graph, solution)
        if md:
            if md.get('ri', None) is not None:
                return self._route_distance(graph, solution[md['ri']])
            if md['f']:
                value += md['lambda'] * sum(
                    [md['p'][(a, b)] * graph.costs[(a, b)] for a, b in md['f']])
        return value


# penalties
def _choose_current_features(graph, solution, md):
    """Choose features to penalize"""
    edges = []
    for route in solution:
        for i in range(len(route)-1):
            edges.append((route[i], route[i+1]))
    return edges


def _most_utilized_feature(graph, md):
    """Choose feature that has the highest utility function value"""
    return sorted(
        [((a, b), graph.costs[(a, b)] / (md['p'][(a, b)] + 1)) for a, b in md['f']],
        key=lambda x: x[1],
        reverse=True)[0][0]


def guided_local_search(graph, penalty_factor, max_iter):
    """Guided local search algorithm"""
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

    O = GlsObjective()
    MD = {
        'p': PenaltyMap(graph.raw_data),  # penalties
        'lambda': penalty_factor,
        'f': [],  # feature set,
        'ignore_feasibility': False
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
        MD['f'] = _choose_current_features(graph, S, MD)
        most_utilized = _most_utilized_feature(graph, MD)
        MD['p'][most_utilized] += 1
        S = search.local_search(graph, O, S, MD)

        if VERBOSE and i % 200 == 0:
            print("O* so far:", O(graph, best_S, None))

        if O(graph, S, None) >= O(graph, best_S, None):
            # due to deterministic behavior of the local search, once objective
            # function stops decreasing, best solution found
            break
        else:
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
        S = guided_local_search(graph, args.penalty_factor, args.max_iter)
        elapsed = time.time() - start
        if VERBOSE:
            print('O* = {o}'.format(o=GlsObjective()(graph, S, None)))
            print('All served?', S.all_served(graph.customer_number))
            print('Everything satisfied?', satisfies_all_constraints(graph, S))
            print('----- PERFORMANCE -----')
            print('GLS took {some} seconds'.format(some=elapsed))
            print('-'*100)
            # visualize(S)
        if not args.no_sol:
            filedir = os.path.dirname(os.path.abspath(__file__))
            generate_sol(graph, S, cwd=filedir, prefix='_gls_')
    return 0


if __name__ == '__main__':
    VERBOSE = True
    sys.exit(main())
