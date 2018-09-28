#!/usr/bin/env python3

import argparse
import sys
import time

# local imports
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


# def local_search(current, graph, max_iter):
#     """Perform local search"""
#     ref_objective = graph.objective()
#     costs = graph.costs[current]
#     iteration = 0
#     for iteration in range(max_iter):
#         min_idx, min_value = min(enumerate(costs), key=lambda x: x[1])
#         if (graph.objective(exclude=current.id) + min_value) < ref_objective:
#             return min_idx
#     return iteration


def main():
    """Main entry point"""
    args = parse_args()
    graph = None
    with open(args.instance) as instance_file:
        graph = GraphUtils(instance_file)
    start = time.time()
    S = search.construct_initial_solution(graph, ignore_constraints=True)
    print('All served?', S.all_served(graph.customer_number))
    print('----- PERFORMANCE -----')
    print('Time for VRP {some} seconds'.format(
        some=(time.time() - start)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
