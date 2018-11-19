#!/usr/bin/env python3
"""
GA solver for quadratic assignment problem
"""

import argparse
import time
import os
import sys
from copy import deepcopy


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
    import lib.search_utils as search
    from lib.problem_utils import Problem
    from lib.problem_utils import QapObjective
    from lib.generate_output import generate_sol
    from lib.constraints import satisfies_constraints


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("QAP problem parser")
    parser.add_argument('instances',
        nargs='+',
        help='VNS problem instance(s)')
    parser.add_argument('--no-sol',
        action='store_true',
        help='Specifies, whether solution files needs to be generated')
    parser.add_argument('--time-limit',
        help='Algorithm time limit (in seconds)',
        type=int,
        default=60*60)
    parser.add_argument('--max-iter',
        help='Algorithm max iterations',
        type=int,
        default=1000)
    parser.add_argument('--population',
        help='Maintained population size',
        type=int,
        default=30)
    return parser.parse_args()


def genetic_algorithm(problem, time_limit, max_iter):
    """GA main entry point"""
    # O - objective function
    # S - current solution
    # best_S <=> S*
    # MD - method specific supplementary data
    search.set_seed(11)
    best_S = None
    O = QapObjective()
    P = search.create_initial_population(problem)
    for p in P:
        if not satisfies_constraints(problem, p):
            raise ValueError('initial solution is infeasible')
    best_S = sorted([p for p in P], key=lambda x: O(problem, x))[0]
    best_O = O(problem, best_S)

    for i in range(max_iter):
        if i % 100 == 0:
            print('So far O* = {o}'.format(o=best_O))
        parents = deepcopy(P)
        P = search.select(problem, O, P)
        P = search.reproduce(problem, P)
        P = search.mutate(problem, P)
        P = search.replace(problem, parents, P)
        curr_best_S = sorted([p for p in P], key=lambda x: O(problem, x))[0]
        curr_best_O = O(problem, curr_best_S)
        if curr_best_O >= best_O:
            continue
        best_S = curr_best_S
        best_O = curr_best_O
    return best_S


def main():
    """Main entrypoint"""
    args = parse_args()
    print(args.instances)
    for instance in args.instances:
        name = os.path.splitext(os.path.basename(instance))[0]
        with open(instance, 'r') as instance_file:
            problem = Problem(instance_file)
            problem.population_size = args.population
        print('-'*100)
        print('File: {name}.txt'.format(name=name))
        start = time.time()
        S = genetic_algorithm(
            problem, args.time_limit, args.max_iter)
        elapsed = time.time() - start
        if S is None:
            print('! NO SOLUTION FOUND !')
        else:
            print('O* = {o}'.format(o=QapObjective()(problem, S)))
            print('All satisfied?', satisfies_constraints(problem, S))
            print('----- PERFORMANCE -----')
            print('GA took {some} seconds'.format(some=elapsed))
        print('-'*100)
        if S is not None and not args.no_sol:
            filedir = os.path.dirname(os.path.abspath(__file__))
            generate_sol(name, S, cwd=filedir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
