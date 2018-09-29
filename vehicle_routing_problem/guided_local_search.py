#!/usr/bin/env python3

import argparse
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


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("")
    parser.add_argument('instance',
        help='Vehicle Routing Problem instance file')
    parser.add_argument('--max_iter',
        help='Guided Local Search max iterations',
        default=2000)
    parser.add_argument('--penalty_factor',
        help='A penalty factor in objective function (works: 0.1, 0.2, 0.3)',
        default=0.2)
    return parser.parse_args()


class GlsObjective(Objective):
    """Guided local search objective function"""
    def _distance(self, graph, solution):
        """Calculate overall distance"""
        s = 0
        for route in solution:
            s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
        return s

    def __call__(self, graph, solution, md):
        """operator() overload"""
        value = self._distance(graph, solution)
        if md and md['f']:
            value += md['lambda'] * sum([md['p'][[a, b]] * graph.costs[[a, b]] for a, b in md['f']])
        return value


def guided_local_search(graph, penalty_factor, max_iter):
    """Guided local search algorithm"""
    # O - objective function
    # S - current solution
    # best_S <=> S*
    # MD - method specific supplementary data

    # some progressbar to show how method is doing
    progress = progressbar.ProgressBar(
        maxval=max_iter,
        widgets=[
            progressbar.Bar('=', '[', ']'),
            ' ',
            progressbar.Percentage()])

    O = GlsObjective()
    MD = {
        'p': PenaltyMap(graph.raw_data),  # penalties
        'lambda': penalty_factor,
        'f': []  # feature set
    }
    S = search.construct_initial_solution(graph, ignore_constraints=True)
    best_S = S

    if VERBOSE:
        print('O={o}'.format(o=O(graph, S, None)))
        progress.start()

    for i in range(max_iter):
        if VERBOSE:
            progress.update(i+1)
        MD['f'] = search.choose_penalty_features(graph, S, MD)
        for a, b in MD['f']:
            MD['p'][[a, b]] += 1
        S = search.local_search(graph, O, S, MD)
        if O(graph, S, MD) < O(graph, best_S, MD):
            best_S = S

    if VERBOSE:
        progress.finish()

    # final LS with no penalties to get true local min
    return search.local_search(graph, O, best_S, None)


def main():
    """Main entry point"""
    args = parse_args()
    graph = None
    with open(args.instance) as instance_file:
        graph = Graph(instance_file)
    start = time.time()
    S = guided_local_search(graph, args.penalty_factor, args.max_iter)
    elapsed = time.time() - start
    if VERBOSE:
        print('O*={o}'.format(o=GlsObjective()(graph, S, None)))
        print('All served?', S.all_served(graph.customer_number))
        print('----- PERFORMANCE -----')
        print('VRP took {some} seconds'.format(some=elapsed))
    return 0


if __name__ == '__main__':
    VERBOSE = True
    sys.exit(main())
