"""Customer and Matrix data types"""

class Customer(object):
    """Customer graph node"""
    def __init__(self, row):
        """Init method"""
        self.values = [int(e) for e in row]

    def __len__(self):
        """Length of customer data array"""
        return len(self.values)

    def __eq__(self, other):
        """Equality operator"""
        if isinstance(other, int):
            return self.id == other
        return self.id == other.id

    def __ne__(self, other):
        """Inequality operator"""
        return self.id != other.id

    def __le__(self, other):
        """Less or equal operator"""
        return self.id <= other.id

    def __lt__(self, other):
        """Less than operator"""
        return self.id < other.id

    def __ge__(self, other):
        """Greater or equal operator"""
        return self.id >= other.id

    def __gt__(self, other):
        """Greater than operator"""
        return self.id > other.id

    def __hash__(self):
        """Hash operator"""
        return self.id

    @property
    def id(self):
        """ID of customer"""
        return self.values[0]

    @property
    def x(self):
        """X coordinate"""
        return self.values[1]

    @property
    def y(self):
        """Y coordinate"""
        return self.values[2]

    @property
    def demand(self):
        """Demand"""
        return self.values[3]

    @property
    def ready_time(self):
        """Ready time"""
        return self.values[4]

    @property
    def due_date(self):
        """Due date"""
        return self.values[5]

    @property
    def service_time(self):
        """Service time"""
        return self.values[6]

    @property
    def is_depot(self):
        """Is a depot"""
        return self.id == 0


class Matrix(object):
    """Abstract matrix to store customer info in cells"""
    def __init__(self, rows, operation):
        """Init method"""
        self.elements = {}
        for row in rows:
            self.elements[Customer(row)] = [None] * len(rows)
        for e in self.elements.keys():
            for i, other in enumerate(self.elements.keys()):
                self.elements[e][i] = operation(e, other)
        self._depot_customer = None
        for c in self.elements.keys():
            if c.is_depot:
                self._depot_customer = c
                break

    def __len__(self):
        """Length per row"""
        return len(self.elements)

    def __getitem__(self, key):
        """Overload for operator[] getter"""
        if isinstance(key, int):  # return customer by index
            return list(self.elements.keys())[key]
        if isinstance(key, list) or isinstance(key, tuple):
            # return specific cost
            key_0, key_1 = key[0], key[1]
            if isinstance(key_0, Customer):
                key_0, key_1 = key_0.id, key_1.id
            return self.elements[key_0][key_1]
        return self.elements[key]  # return all costs per customer

    def __setitem__(self, key, value):
        """Overload for operator[] setter"""
        if isinstance(key, list) or isinstance(key, tuple):
            # set specific cost for customer
            key_0, key_1 = key[0], key[1]
            if isinstance(key_0, Customer):
                key_0, key_1 = key_0.id, key_1.id
            self.elements[key_0][key_1] = value
        elif len(value) == len(self.elements[key[0]]):
            self.elements[key[0]] = value  # set all costs for customer
        else:
            pass  # do nothing

    def __str__(self):
        """Serialize matrix"""
        return self.elements.__str__()

    @property
    def depot(self):
        """Return depot"""
        return self._depot_customer

    @property
    def customers(self):
        """Get customers matrix"""
        return self.elements
