class Customer(object):
    """Customer graph node"""
    def __init__(self, row):
        """Init method"""
        self.values = [int(e) for e in row]

    def __len__(self):
        """Length of customer data array"""
        return len(self.values)

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
        self.elements = []
        for row in rows:
            self.elements.append(Customer(row))
        # sort elements by id
        self.elements = sorted(self.elements, key=lambda c: c.id)
        self.matrix = [[None]*len(self)]*len(self)
        for i, c1 in enumerate(self.elements):
            for j, c2 in enumerate(self.elements):
                self.matrix[i][j] = operation(c1, c2)
        self.depot_index = None
        for i, c in enumerate(self.elements):
            if c.is_depot:
                self.depot_index = i
                break

    def __len__(self):
        """Length per row"""
        return len(self.elements)

    def __getitem__(self, key):
        """Overload for operator[] getter"""
        if isinstance(key, list):
            return self.matrix[key[0]][key[1]]
        return self.elements[key]

    def __setitem__(self, key, value):
        """Overload for operator[] setter"""
        if isinstance(key, list):
            self.matrix[key[0]][key[1]] = Customer(value)
        else:
            self.elements[key] = Customer(value)

    def __str__(self):
        """Serialize matrix"""
        return self.matrix.__str__()

    @property
    def depot_idx(self):
        """Get depot index"""
        return self.depot_index

    @property
    def customers(self):
        """Get customers matrix"""
        return self.elements
