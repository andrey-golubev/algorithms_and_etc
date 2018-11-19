"""
Search utilities
"""
import concurrent.futures as futures
import multiprocessing
from copy import deepcopy
from collections import namedtuple
import numpy as np
import random


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
    from constraints import satisfies_constraints
    from problem_utils import Solution


def set_seed(seed):
    """Seed the numpy random number generator"""
    np.random.seed(seed)


# initial
def create_initial_population(problem):
    """Create initial population"""
    population = []
    for _ in range(problem.population_size * 2):
        population.append(Solution(list(np.random.permutation(
            range(problem.n)))))
    return population


# selection
def select(problem, objective, population):
    """Select best individuals in population"""
    probabilities = [objective(problem, i) for i in population]
    total_fitness = sum(probabilities)
    probabilities = [f / total_fitness for f in probabilities]
    selected = []
    indices = np.random.choice([i for i in range(len(population))],
        replace=False, p=probabilities, size=int(len(population) / 2))
    for i in indices:
        selected.append(population[i])
    return selected


# cross-over
def reproduce(problem, parents):
    """Apply two point cross-over on parents"""
    if len(parents) % 2 != 0:
        raise ValueError('parents number is not even')
    n = problem.n
    # shuffle parents
    np.random.shuffle(parents)
    # for each pair of parents:
    # child 1: fix "center", reverse "corners"
    # child 2: reverse "center", fix "corners"
    # => 1 parent produces 2 children
    children = []
    for p in parents:
        first, second = np.random.choice([i for i in range(1, n)], size=2,
            replace=False)
        if first >= second:
            first, second = second, first
        reversed_p = list(reversed(p))
        children.append(
            reversed_p[:first] + p[first:second] + reversed_p[second:])
        children.append(
            p[:first] + reversed_p[first:second] + p[second:])
    return children


# mutation
def mutate(problem, population):
    """Mutate the population"""
    prob = 1 / problem.n  # mutation probability for gene
    # for each individual: find two indices, swap values at the indices
    for i, individual in enumerate(population):
        mutation_indices = []
        for gene_id in range(problem.n):
            if np.random.choice([True, False], size=1, p=[prob, 1 - prob]):
                mutation_indices.append(gene_id)
            if len(mutation_indices) == 2:
                break
        if len(mutation_indices) == 2:
            k, r = mutation_indices[0], mutation_indices[1]
            individual[k], individual[r] = individual[r], individual[k]
            population[i] = individual
    return population


# replacement
def replace(problem, parents, children):
    """Apply steady-state-no-duplicates replacement

    Can potentially result in delete-all strategy if N becomes equal to a number
    of maintained population
    """
    # n = np.random.randint(len(parents) / 3, len(parents))
    # indices = np.random.choice([i for i in range(len(parents))], size=n,
    #     replace=False)
    # for i in indices:
    #     parents[i] = children[i]
    # return parents
    return children
