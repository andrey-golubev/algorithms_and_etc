"""Library for graph visualization"""

import matplotlib.pyplot as plt
import numpy as np


def visualize(solution):
    """Visualize routes given solution"""
    cmap = plt.get_cmap('gnuplot')
    colors = [cmap(i) for i in np.linspace(0, 1, len(solution))]
    for i, route in enumerate(solution):
        for ci in range(len(route)-1):
            c1 = route[ci]
            c2 = route[ci+1]
            x = [c1.x, c2.x]
            y = [c1.y, c2.y]
            plt.plot(x, y, 'ro-', color=colors[i])
    plt.show()
