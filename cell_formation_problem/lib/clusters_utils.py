"""
Clusters utilities
"""

class Scheme(object):
    """Scheme of machines and corresponding parts"""
    def __init__(self, io_stream):
        m, p, data = Scheme.parse_instance(io_stream)
        self._mn = m
        self._pn = p
        self._data = data

    @property
    def machine_number(self):
        """Get total number of machines"""
        return self._mn

    @property
    def parts_number(self):
        """Get total number of parts used"""
        return self._pn

    @property
    def machine_ids(self):
        """Get machine ids"""
        return self._data.keys()

    def processed_parts(self, machine_id):
        """Get list of parts processed by machine"""
        return self._data[machine_id]

    @staticmethod
    def parse_instance(io_stream):
        """Parse CFP instance file"""
        m, p = io_stream.readline().split()
        machine_to_parts = {}
        for line in io_stream.readlines():
            if not line:
                continue
            line = line.split()
            m_id = int(line[0])
            parts = [int(e) for e in line[1:]]
            machine_to_parts[m_id] = parts
        return m, p, machine_to_parts
