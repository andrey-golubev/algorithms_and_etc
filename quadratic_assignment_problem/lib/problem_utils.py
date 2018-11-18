"""Problem utilities"""
from copy import copy as shallowcopy
from decimal import Decimal


class Solution(object):
    """
    QAP solution representation
    """
    def __init__(self, assigned_locations):
        """Init method"""
        # indices are facilities, values are locations
        self._locations = assigned_locations

    def __getitem__(self, facility_index):
        """Operator[]"""
        return self._locations[facility_index]

    def __eq__(self, other):
        """Equality operator"""
        return self._locations == other._locations

    def __neq__(self, other):
        """Inequality operator"""
        return not (self == other)

    def __len__(self):
        """Length of solution"""
        return len(self._locations)


class Problem(object):
    """Problem utility class"""
    def __init__(self, io_stream):
        self._n, self._distances, self._flows = Problem.parse_instance(
            io_stream)

    @property
    def distances(self):
        """Return distances matrix"""
        return self._distances

    @property
    def flows(self):
        """Return flow matrix"""
        return self._flows

    @property
    def n(self):
        """Get number of plants/locations"""
        return self._n

    @staticmethod
    def parse_instance(io_stream):
        """Parse CFP instance file"""
        n = int(io_stream.readline().strip())
        # read distances matrix:
        distances = []
        row = io_stream.readline().strip()
        while row:
            data_row = [int(v) for v in row.split()]
            distances.append(data_row)
            row = io_stream.readline().strip()
        # read flows matrix:
        flows = []
        for row in io_stream.readlines():
            row = row.strip()
            if not row:
                continue
            data_row = [int(v) for v in row.split()]
            flows.append(data_row)
        return n, distances, flows


class QfpObjective():
    """Quadratic assignment problem objective function"""
    def __call__(self, problem, solution):
        """
        Calculate objective function value for solution

        operator() implementation
        :param problem:
            Problem object
        :param solution:
            Solution object
        """
        distance = lambda i, j: problem.distances[i][j]
        obj = 0
        for i in range(problem.n):
            for j in range(problem.n):
                obj += problem.flows[i][j] * distance(solution[i], solution[j])
        return obj
