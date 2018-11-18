import os


def generate_sol(name, solution, cwd):
    """Generate <instance name>.sol"""
    filename = '{name}.sol'.format(name=name)
    filepath = os.path.join(os.path.abspath(cwd), '_results')
    try:
        os.makedirs(filepath)
    except:
        pass  # skip if exists
    filepath = os.path.join(filepath, filename)
    with open(filepath, 'w') as sol_file:
        out = ' '.join(str(e) for e in sorted(range(len(solution)),
            key=lambda k: solution[k]))
        sol_file.write(out)
        sol_file.write('\n')
