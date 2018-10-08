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
    from lib.clusters_utils import Scheme


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
    return parser.parse_args()


def variable_neighbourhood_search(scheme):
    """VNS main entry point"""
    return 0


def main():
    """Main entrypoint"""
    args = parse_args()
    print(args.instances)
    for instance in args.instances:
        name = os.path.basename(instance)
        with open(instance, 'r') as instance_file:
            scheme = Scheme(instance_file)
        print('-'*100)
        print('File: {name}'.format(name=name))
        start = time.time()
        S = variable_neighbourhood_search(scheme)
        elapsed = time.time() - start
        print('VNS took {some} seconds'.format(some=elapsed))
        print('-'*100)

        if S is not None and not args.no_sol:
            pass

    return 0

if __name__ == '__main__':
    sys.exit(main())
