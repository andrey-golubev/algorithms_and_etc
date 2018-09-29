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
    from lib.matrix import Matrix


def objective(solution):
    """Calculate objective function"""
    return 0


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
        routes = []
        for route in self.routes:
            routes.append([c.id for c in route])
        return routes.__str__()

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

    def all_served(self, number_of_customers):
        """Return whether all customers are served"""
        served_customers = set()
        for route in self.routes:
            served_customers |= {c.id for c in route}
        return len(served_customers) == number_of_customers


class Objective(ABC):
    """Objective function interface"""
    @abstractmethod
    def __call__(self, graph, solution, penalties):
        """operator() interface"""
        del graph
        del solution
        del penalties
        return 0

class CostMap(Matrix):
    """
    Cost map between customers
    """

    def __init__(self, customers):
        """Init method"""
        super(CostMap, self).__init__(customers, CostMap.calculate_cost)

    @staticmethod
    def calculate_cost(a, b):
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


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


class GraphUtils(object):
    """
    Main class for graph abstraction
    """

    def __init__(self, io_stream):
        """Init method"""
        _name, number, cap, input_data = GraphUtils.parse_instance(io_stream)
        self.instance_name = _name
        self.v_number = number
        self.vehicle_capacity = cap
        # input data processing:
        # expecting full graph!
        self.cost_map = CostMap(input_data)
        self.c_number = len(input_data)

    @property
    def name(self):
        """Instance name"""
        return self.instance_name

    @property
    def capacity(self):
        """Vehicle capacity"""
        return self.vehicle_capacity

    @property
    def vehicle_number(self):
        return self.v_number

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
        """Return depot"""
        return self.costs.depot

    @property
    def customers(self):
        """Return customers"""
        return self.costs.customers.keys()

    # def objective(self, exclude=[]):
    #     """Calculate objective function"""
    #     if not (isinstance(exclude, list)):
    #         exclude = [exclude]
    #     costs = 0
    #     for customer in self.path:
    #         if customer.id in exclude:
    #             continue
    #         costs += self.costs[customer.id]
    #     return costs

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
            name=self.instance_name,
            v_num=self.vehicle_number,
            capacity=self.vehicle_capacity,
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
