"""Internal library for handling constraints"""

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

with import_from('../'):
    from lib.graph import Solution


def _satisfies_time_constraints(graph, solution, route_index=None):
    """Check whether solution satisfies time constraints"""
    indices = range(len(solution)) if route_index is None else [route_index]
    for ri in indices:
        route = solution[ri]
        start_time = 0
        for i in range(len(route)-1):
            # c.ready + c.service + distance(c, next_c) + next_c.service
            # <=
            # next_c.due_date
            c = route[i]
            next_c = route[i+1]
            spent_time_on_c = start_time + c.service_time
            spent_time_on_c += graph.costs[(c, next_c)]
            # decide whether we wait or start right after we arrive
            start_time = max(start_time, spent_time_on_c)
            spent_time_on_c += next_c.service_time
            if spent_time_on_c > next_c.due_date:
                return False
    return True


def _satisfies_capacity_constraint(graph, solution, route_index=None):
    """Check whether solution satisfies capacity constraint"""
    def route_capacity(route):
        return sum(c.demand for c in route)
    indices = range(len(solution)) if route_index is None else [route_index]
    for ri in indices:
        if route_capacity(solution[ri]) > graph.capacity:
            return False
    return True


def _satisfies_number_constraint(graph, solution, route_index=None):
    """Check whether solution satisfies vehicle number constraint"""
    if route_index is not None:
        # meaningless to check solution's conditions on single route
        return True
    return len(solution) <= graph.vehicle_number


def _satisfies_service_constraint(graph, solution, route_index=None):
    """Check whether solution satisfies customer service constraint"""
    if route_index is not None:
        # meaningless to check solution's conditions on single route
        return True
    return solution.all_served(graph.customer_number)


def satisfies_all_constraints(graph, solution, route_index=None, excludes=[]):
    """Check whether solution satisfies all included constraints"""
    satisfies = True
    constraints = {
        'time': _satisfies_time_constraints,
        'capacity': _satisfies_capacity_constraint,
        'number': _satisfies_number_constraint,
        'service': _satisfies_service_constraint
    }
    for check in excludes:  # exclude not needed checks
        constraints.pop(check, None)
    for checker in constraints.values():
        res = checker(graph, solution, route_index)
        satisfies &= res
    return satisfies


def route_satisfies_constraints(graph, route):
    """Check whether route satisfies all constraints"""
    return satisfies_all_constraints(
        graph, Solution(routes=[route]), route_index=0)
