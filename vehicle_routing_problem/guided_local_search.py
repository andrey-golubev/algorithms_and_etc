#!/usr/bin/env python3

import argparse
import sys

# local imports
from lib.graph_utils import GraphUtils


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


def local_search(current, graph, max_iter):
    """Perform local search"""
    ref_objective = graph.objective()
    costs = graph.costs[current]
    iteration = 0
    for iteration in range(max_iter):
        min_idx, min_value = min(enumerate(costs), key=lambda x: x[1])
        if (graph.objective(exclude=current.id) + min_value) < ref_objective:
            return min_idx
    return iteration


def main():
    """Main entry point"""
    args = parse_args()
    graph = GraphUtils(args.instance)
    print(local_search(0, graph, args.ls_max_iter))
    # print(graph)
    return 0


if __name__ == '__main__':
    sys.exit(main())
