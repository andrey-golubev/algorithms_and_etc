"""Graph utils, Solution, Objective function"""

from abc import ABC, abstractmethod
import math

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
    from lib.customer import Matrix


class Solution(object):
    """
    VRP solution representation
    """
    def __init__(self, routes):
        """Init method"""
        self._routes = routes

    def changed(self, route, route_index):
        """Return new changed solution with new route"""
        routes = list(self._routes)
        routes[route_index] = route
        return Solution(routes)

    def __str__(self):
        """Serialize solution"""
        return self.ids().__str__()

    def __getitem__(self, key):
        """Return route by key(index)"""
        if not isinstance(key, int):
            raise ValueError('wrong key type')
        return self._routes[key]

    def __len__(self):
        """Return length of solution: number of routes"""
        return len(self._routes)

    def __eq__(self, other):
        """Equality operator"""
        return self.routes == other.routes

    def __ne__(self, other):
        """Inequality operator"""
        return self.routes != other.routes

    @property
    def routes(self):
        """Get all paths"""
        return self._routes

    @property
    def shape(self):
        """Return number of routes and customers served"""
        served_customers = set()
        for route in self.routes:
            served_customers |= {c.id for c in route}
        return len(self._routes), len(served_customers)

    def find_route(self, customer):
        """Find which route customer belongs to"""
        for ri, route in enumerate(self.routes):
            for i, c in enumerate(route):
                if customer == c:
                    return ri, i
        return None, None

    def all_served(self, number_of_customers):
        """Return whether all customers are served"""
        served_customers = set()
        for route in self.routes:
            served_customers |= {c.id for c in route}
        return len(served_customers) >= number_of_customers

    def ids(self):
        """Return routes with customer.id as nodes"""
        ids = []
        for route in self._routes:
            ids.append([c.id for c in route])
        return ids

    def append(self, routes):
        """Append route to solution"""
        for route in routes:
            if not isinstance(route, list):
                continue
            self._routes.append(route)
        return self

class Objective(ABC):
    """Objective function interface"""
    @abstractmethod
    def __call__(self, graph, solution, md):
        """
        operator() interface

        :param graph:
            Graph object
        :param solution:
            Solution object
        :param md:
            Specific method supplementary data as a dict (i.e. {'p': penalties})
        """
        del graph
        del solution
        del md
        return 0

    def _distance(self, graph, solution):
        """Calculate overall distance"""
        s = 0
        for route in solution:
            s += sum(graph.costs[(route[i], route[i+1])] for i in range(len(route)-1))
        return s

    def _route_distance(self, graph, route):
        """Calculate route distance"""
        return sum(graph.costs[(route[i], route[i+1])] for i in range(len(route)-1))


class CostMap(Matrix):
    """
    Costs between customers
    """
    def __init__(self, customers):
        """Init method"""
        super(CostMap, self).__init__(customers, CostMap.calculate_cost)

    @staticmethod
    def calculate_cost(a, b):
        """Cost function"""
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


class PenaltyMap(Matrix):
    """
    Penalties between customers
    """
    def __init__(self, customers):
        """Init method"""
        super(PenaltyMap, self).__init__(customers, lambda x, y: 0)


def _skip_lines(input_file, keyword):
    """
    Skip lines in input file until keyword is met
    Next line after keyword line is read
    """
    dummy = ''
    while True:
        dummy = input_file.readline().strip()
        if dummy == keyword:
            dummy = input_file.readline()
            break
    return input_file


class Graph(object):
    """
    Main class for graph abstraction
    """
    def __init__(self, io_stream):
        """Init method"""
        _name, number, cap, input_data = Graph.parse_instance(io_stream)
        self._instance_name = _name.lower()
        self._v_number = number
        self._v_capacity = cap
        # input data processing:
        # expecting full graph!
        self._input_data = input_data
        self.cost_map = CostMap(input_data)
        self.c_number = len(input_data)
        # find distance to neighbours of each customer
        self._neighbours_map = {}
        for customer in self.cost_map.customers:
            self._neighbours_map[customer] = sorted(
                [(other, self.cost_map[[customer, other]]) \
                    for other in self.customers if other != customer],
                key=lambda x: x[1])
        self._avg_cap = sum(c.demand for c in self.customers) / self._v_number

    @property
    def name(self):
        """Instance name"""
        return self._instance_name

    @name.setter
    def name(self, value):
        """Instance name setter"""
        self._instance_name = value

    @property
    def capacity(self):
        """Vehicle capacity"""
        return self._v_capacity

    @property
    def vehicle_number(self):
        """Number of vehicles"""
        return self._v_number

    @property
    def costs(self):
        """Costs map"""
        return self.cost_map

    @property
    def customer_number(self):
        """Number of customers"""
        return self.c_number

    @property
    def depot(self):
        """Depot"""
        return self.costs.depot

    @property
    def customers(self):
        """All customers"""
        return self.costs.customers.keys()

    @property
    def raw_data(self):
        """Raw input data"""
        return self._input_data

    @property
    def neighbours(self):
        """Map of neighbours of each customer"""
        return self._neighbours_map

    @property
    def avg_capacity(self):
        """Average capacity of each route"""
        return self._avg_cap

    def __len__(self):
        """Number of customers"""
        return len(self.cost_map)

    def __str__(self):
        """Serialize into str"""
        return """{name}
vehicle: #num={v_num} #capacity={capacity}
customer: #num={c_num}
costs:
{cost_map}
""".format(
            name=self.name,
            v_num=self.vehicle_number,
            capacity=self.capacity,
            c_num=self.customer_number,
            cost_map=[],
            #cost_map=self.cost_map
        )

    @staticmethod
    def parse_instance(io_stream):
        """Parse VRP instance file"""
        name = io_stream.readline().strip()
        io_stream = _skip_lines(io_stream, 'VEHICLE')
        number, capacity = io_stream.readline().strip().split()
        io_stream = _skip_lines(io_stream, 'CUSTOMER')
        customer_data = []
        for customer_str in io_stream.readlines():
            customer_str = customer_str.strip()
            if not customer_str:
                continue
            customer_data.append(customer_str.split())
        return name, int(number), int(capacity), customer_data
