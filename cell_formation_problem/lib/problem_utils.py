"""Problem utilities"""

from copy import copy as shallowcopy


class Solution(object):
    """
    CFP solution representation
    """
    def __init__(self, clusters):
        """Init method"""
        # machine clusters (cells), parts clusters (cells)
        self._m_c, self._p_c = clusters

    def __getitem__(self, t):
        """Get clustered machines or parts"""
        if t not in ['m', 'p']:
            raise ValueError('wrong cluster type')
        if t == 'm':
            return self._m_c
        if t == 'p':
            return self._p_c

    def __eq__(self, other):
        """Equality operator"""
        return self._m_c == other._m_c and self._p_c == other._p_c

    def __neq__(self, other):
        """Inequality operator"""
        return not (self == other)

    @property
    def number_of_clusters(self):
        """
        Get number of clusters

        Usage of same clusters for machines and parts is enforced by constraints
        """
        return len(set(self._m_c))

    @property
    def shape(self):
        """Get shape of solution: M x P"""
        return len(self._m_c), len(self._p_c)

    @staticmethod
    def from_clusters(scheme, clusters):
        """Construct Solution object from list of Cluster objects"""
        machine_clusters = [None]*scheme.machines_number
        parts_clusters = [None]*scheme.parts_number
        for cluster in clusters:
            for m_id in cluster.machines:
                machine_clusters[m_id] = cluster.id
            for p_id in cluster.parts:
                parts_clusters[p_id] = cluster.id
        if any(e is None for e in machine_clusters):
            raise ValueError('given clusters incomplete')
        if any(e is None for e in parts_clusters):
            raise ValueError('given clusters incomplete')
        return Solution((machine_clusters, parts_clusters))


class Scheme(object):
    """Scheme of machines and corresponding parts"""
    def __init__(self, io_stream):
        m, p, data = Scheme.parse_instance(io_stream)
        self._mn = m
        self._pn = p
        self._matrix = data
        self._n1 = 0
        for row in self._matrix:
            self._n1 += sum(row)

    @property
    def machines_number(self):
        """Get total number of machines"""
        return self._mn

    @property
    def parts_number(self):
        """Get total number of parts used"""
        return self._pn

    @property
    def shape(self):
        """Get matrix shape: m x p"""
        return self._mn, self._pn

    @property
    def matrix(self):
        """Return machine-part matrix"""
        return self._matrix

    @property
    def n1(self):
        """Get total number of operations"""
        return self._n1

    @staticmethod
    def parse_instance(io_stream):
        """Parse CFP instance file"""
        m, p = io_stream.readline().split()
        m, p = int(m), int(p)
        matrix = []
        for _ in range(m):
            matrix.append([0] * p)
        for line in io_stream.readlines():
            if not line:
                continue
            line = line.split()
            m_id = int(line[0]) - 1  # zero-based
            part_ids = [int(e) for e in line[1:]]
            for part_id in part_ids:
                part_id -= 1  # zero-based
                matrix[m_id][part_id] = 1
        return m, p, matrix


class CfpObjective():
    """Cell formation problem objective function"""
    def __call__(self, scheme, solution):
        """
        Calculate objective function value for solution

        operator() implementation
        :param scheme:
            Scheme object
        :param solution:
            Solution object
        """
        n1 = scheme.n1
        n1_in = 0
        n0_in = 0
        matrix = scheme.matrix
        for m_id, parts in enumerate(matrix):
            for p_id, value in enumerate(parts):
                # if machine and part in one cluster (cell):
                # n1_in += element value
                # n0_in += 1 - element value
                if solution['m'][m_id] == solution['p'][p_id]:
                    n1_in += value
                    n0_in += 1 - value
        return n1_in / (n1 + n0_in)

    @staticmethod
    def cluster_objective(scheme, cluster):
        """
        Calculate objective function value for cluster

        :param scheme:
            Scheme object
        :param cluster:
            Cluster object (a.k.a. cell)
        """
        n1 = scheme.n1
        n1_in = 0
        n0_in = 0
        matrix = scheme.matrix
        for m_id in cluster.machines:
            for p_id in cluster.parts:
                value = matrix[m_id][p_id]
                n1_in += value
                n0_in += 1 - value
        return n1_in / (n1 + n0_in)


class Cluster(object):
    """Cluster object"""
    def __init__(self, scheme, cluster_id, machines, parts):
        """Init method"""
        self.id = cluster_id
        self.machines = set(machines)
        self.parts = set(parts)
        self._scheme = shallowcopy(scheme)

    def _components_lengths_equal(self, value):
        """
        Check if machines, parts components lengths are equal to value
        """
        return len(self.machines) == value and len(self.parts) == value

    @property
    def value(self):
        """Calculate objective value for cluster"""
        return CfpObjective.cluster_objective(self._scheme, self)

    @property
    def can_split(self):
        """Check whether cluster can be split"""
        # can split if at least 2 machines and 2 parts
        return len(self.parts) > 1 and len(self.machines) > 1

    @property
    def empty(self):
        """Check whether cluster is empty"""
        return self._components_lengths_equal(0)

    @property
    def near_empty(self):
        """
        Check whether cluster is nearly empty (contains 1 machine or 1 part)
        """
        return self._components_lengths_equal(1)


def construct_clusters(scheme, solution):
    """Construct clusters from solution"""
    cells = {}
    for cluster_id in range(solution.number_of_clusters):
        cells[cluster_id] = cells.get(cluster_id, {'m': set(), 'p': set()})
        for m_id, m_c in enumerate(solution['m']):
            if cluster_id != m_c:
                continue
            cells[cluster_id]['m'].add(m_id)
        for p_id, p_c in enumerate(solution['p']):
            if cluster_id != p_c:
                continue
            cells[cluster_id]['p'].add(p_id)
    clusters = []
    for c_id in cells.keys():
        cell = cells[c_id]
        clusters.append(Cluster(scheme, c_id, cell['m'], cell['p']))
    return sorted(clusters, key=lambda c: c.value)
