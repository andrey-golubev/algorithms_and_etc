#!/usr/bin/env python3

import argparse
import sys
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
    import lib.search_utils as search


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("")
    parser.add_argument('instance',
        help='Vehicle Routing Problem instance file')
    parser.add_argument('--ls_max_iter',
        help='Local Search max iterations',
        default=500)
    return parser.parse_args()


def optimal_start_times(graph):
    """Compute optimal start times of services"""
    return graph


class GlsObjective(Objective):
    """Guided local search objective function"""
    def __init__(self):
        """Init method"""
        def distance(graph, solution, method_specific):
            """Calculate overall distance"""
            del method_specific
            s = 0
            for route in solution:
                s += sum(graph.costs[[route[i], route[i+1]]] for i in range(len(route)-1))
            return s
        self.distance = distance

    def __call__(self, graph, solution, method_specific):
        """operator() overload"""
        return self.distance(graph, solution, method_specific)


def main():
    """Main entry point"""
    args = parse_args()
    graph = None
    with open(args.instance) as instance_file:
        graph = Graph(instance_file)
    objective_function = GlsObjective()
    start = time.time()
    S = search.construct_initial_solution(graph, ignore_constraints=True)
    S = search.local_search(graph, objective_function, S)
    print('All served?', S.all_served(graph.customer_number))
    print('----- PERFORMANCE -----')
    print('VRP took {some} seconds'.format(
        some=(time.time() - start)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
