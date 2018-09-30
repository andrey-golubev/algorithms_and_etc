"""Internal library with constraints checking"""

def _satisfies_time_constraints(graph, solution):
    """Check whether solution satisfies time constraints"""
    for route in solution:
        for i in range(len(route)-1):
            # c.ready_time + c.service_time + distance(c, next_c) <= next_c.due_date
            c = route[i]
            next_c = route[i+1]
            spent_time_on_c = c.ready_time + c.service_time
            spent_time_on_c += graph.costs[[c, next_c]]
            if spent_time_on_c > next_c.due_date:
                return False
    return True


def _satisfies_capacity_constraint(graph, solution):
    """Check whether solution satisfies capacity constraint"""
    for route in solution:
        if sum(c.demand for c in route) > graph.vehicle_capacity:
            return False
    return True


def _satisfies_number_constraint(graph, solution):
    """Check whether solution satisfies vehicle number constraint"""
    return len(solution) <= graph.vehicle_number


def _satisfies_service_constraint(graph, solution):
    """Check whether solution satisfies customer service constraint"""
    return solution.all_served(graph.customer_number)


def satisfies_all_constraints(graph, solution, excludes=[]):
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
    for name, checker in constraints.items():
        res = checker(graph, solution)
        satisfies &= res
        # if res is False:
            # print('Failed:', name)
    return satisfies
