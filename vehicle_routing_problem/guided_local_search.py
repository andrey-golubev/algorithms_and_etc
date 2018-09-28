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
    from lib.graph_utils import GraphUtils
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


def main():
    """Main entry point"""
    args = parse_args()
    graph = None
    with open(args.instance) as instance_file:
        graph = GraphUtils(instance_file)
    start = time.time()
    S = search.construct_initial_solution(graph, ignore_constraints=True)
    S = search.local_search(graph, S)
    print('All served?', S.all_served(graph.customer_number))
    print('----- PERFORMANCE -----')
    print('VRP took {some} seconds'.format(
        some=(time.time() - start)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
