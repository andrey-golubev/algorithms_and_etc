import os

def generate_sol(graph, solution, cwd):
    """Generate <instance name>.sol"""
    filename = '{name}.sol'.format(name=graph.name)
    filepath = os.path.join(os.path.abspath(cwd), '_logs')
    try:
        os.makedirs(filepath)
    except:
        pass  # skip if exists
    filepath = os.path.join(filepath, filename)
    pattern = '{id} {start} '
    with open(filepath, 'w+') as sol_file:
        for route in solution:
            route_str = pattern.format(id=0, start=0)
            start_time = 0
            for i in range(1, len(route)):
                # c.ready + c.service + distance(c, next_c) + next_c.service
                # <=
                # next_c.due_date
                c = route[i-1]
                next_c = route[i]
                spent_time_on_c = start_time + c.service_time
                spent_time_on_c += graph.costs[(c, next_c)]
                # decide whether we wait or start right after we arrive
                start_time = max(spent_time_on_c, next_c.ready_time)
                route_str += pattern.format(id=next_c.id, start=start_time)
            sol_file.write(route_str.strip())
            sol_file.write('\n')
