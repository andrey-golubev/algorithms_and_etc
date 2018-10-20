import os


def generate_sol(name, solution, cwd):
    """Generate <instance name>.sol"""
    filename = '{name}.sol'.format(name=name)
    filepath = os.path.join(os.path.abspath(cwd), '_cfp_logs_vns_general')
    try:
        os.makedirs(filepath)
    except:
        pass  # skip if exists
    filepath = os.path.join(filepath, filename)
    with open(filepath, 'w') as sol_file:
        m_out = ' '.join([str(e) for e in solution['m']])
        p_out = ' '.join([str(e) for e in solution['p']])
        sol_file.write(m_out)
        sol_file.write('\n')
        sol_file.write(p_out)
        sol_file.write('\n')
