"""Problem utilities"""


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

    @property
    def number_of_clusters(self):
        return len(set(self._m_c))

    @property
    def shape(self):
        """Get shape of solution: M x P"""
        return len(self._m_c), len(self._p_c)


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
        operator() interface
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
