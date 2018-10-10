#!/usr/bin/env python3
"""
General VNS solver for cell formation problem
"""

import argparse
import time
import os
import sys

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
    from lib.problem_utils import Scheme
    from lib.problem_utils import CfpObjective
    from lib.generate_output import generate_sol
    from lib.constraints import satisfies_constraints


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser("VNS problem parser")
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
        help='Iterated Local Search max iterations',
        type=int,
        default=2000)
    return parser.parse_args()


def variable_neighbourhood_search(scheme, time_limit, max_iter):
    """VNS main entry point"""
    # O - objective function
    # S - current solution
    # best_S <=> S*
    # MD - method specific supplementary data
    best_S = None
    try:
        O = CfpObjective()
        S = search.create_initial_solution(scheme)
        if not satisfies_constraints(scheme, S):
            raise ValueError('initial solution is infeasible')
        best_S = S
        best_O = O(scheme, best_S)

        start = time.time()
        objective_unchanged = 0
        for i in range(max_iter):
            elapsed = time.time() - start
            if elapsed > time_limit:
                print('-- Timeout reached --')
                raise TimeoutError('algorithm timeout reached')
            S = search.shake(scheme, O, S)
            S = search.local_search(scheme, O, S)
            if i % max_iter / 10 == 0:
                print("O* so far:", best_O)
            if S == best_S:
                # solution didn't change after perturbation + local search
                break
            if objective_unchanged > max_iter * 0.1:
                # if 10% of iterations in a row there's no improvement, stop
                break
            curr_O = O(scheme, S)
            if curr_O <= best_O:
                objective_unchanged += 1
                continue
            objective_unchanged = 0
            best_S = S
            best_O = curr_O
    except TimeoutError:
        pass  # supress timeout errors, expecting only from algo timeout
    except Exception:
        raise
    # finally:
    #     if best_S is None:
    #         return None
    #     return search.local_search(scheme, O, best_S)
    return search.local_search(scheme, O, best_S)


def main():
    """Main entrypoint"""
    args = parse_args()
    print(args.instances)
    for instance in args.instances:
        name = os.path.splitext(os.path.basename(instance))[0]
        with open(instance, 'r') as instance_file:
            scheme = Scheme(instance_file)
        print('-'*100)
        print('File: {name}.txt'.format(name=name))
        start = time.time()
        S = variable_neighbourhood_search(
            scheme, args.time_limit, args.max_iter)
        elapsed = time.time() - start
        if S is None:
            print('! NO SOLUTION FOUND !')
        else:
            print('O* = {o}'.format(o=CfpObjective()(scheme, S)))
            print('Number of clusters: {number}'.format(
                number=S.number_of_clusters))
            print('----- PERFORMANCE -----')
            print('VNS took {some} seconds'.format(some=elapsed))
        print('-'*100)
        if S is not None and not args.no_sol:
            filedir = os.path.dirname(os.path.abspath(__file__))
            generate_sol(name, S, cwd=filedir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
