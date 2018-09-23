import math
from prettytable import PrettyTable

# local imports
from lib.matrix import Matrix


def skip_lines(input_file, keyword):
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


class CostMap(Matrix):
    """Cost map between customers"""
    def __init__(self, customers):
        super(CostMap, self).__init__(customers, CostMap.calculate_cost)

    def __getitem__(self, key):
        """Overload for operator[] getter"""
        return self.matrix[key]  # return row

    def __setitem__(self, key, value):
        """Overload for operator[] setter"""
        if not isinstance(value, list) or len(self.matrix[key]) != len(value):
            raise ValueError
        self.matrix[key] = value

    @staticmethod
    def calculate_cost(a, b):
        return math.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)


class GraphUtils(object):
    """Main class for graph abstraction"""
    def __init__(self, path):
        _name, number, cap, input_data = GraphUtils.parse_instance(path)
        self.instance_name = _name
        self.v_number = number
        self.vehicle_capacity = cap
        # input data processing:
        self.customer_num = 0
        # expecting full graph!
        self.cost_map = CostMap(input_data)
        self.path = []  # customer ids for path

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

    def objective(self, exclude=[]):
        """Calculate objective function"""
        if not (isinstance(exclude, list)):
            exclude = [exclude]
        costs = 0
        for customer in self.path:
            if customer.id in exclude:
                continue
            costs += self.costs[customer.id]
        return costs

    def update_path(self, id_before, id_after):
        """Update path with new node"""
        for i, e in enumerate(self.path):
            if e.id == id_before:
                self.path[i] = self.costs.elements[id_after]
        return self

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
            c_num=self.customer_num,
            cost_map=[],
            #cost_map=self.cost_map
        )

    @staticmethod
    def parse_instance(instance_path):
        """Parse VRP instance file"""
        instance_file = open(instance_path, 'r')
        name = instance_file.readline().strip()
        instance_file = skip_lines(instance_file, 'VEHICLE')
        number, capacity = instance_file.readline().strip().split()
        instance_file = skip_lines(instance_file, 'CUSTOMER')
        customer_data = []
        for customer_str in instance_file.readlines():
            customer_str = customer_str.strip()
            if not customer_str:
                continue
            customer_data.append(customer_str.split())
        instance_file.close()
        return name, number, capacity, customer_data
