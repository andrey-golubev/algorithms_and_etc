#!/usr/bin/env python3

import linecache
import sys
import unittest

def parse_exception():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    funcname = f.f_code.co_name
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'File "{f}", line {num}, in {func}\n\t{line}\n{type}: {error}'.format(
        f=filename,
        num=lineno,
        func=funcname,
        line=line.strip(),
        type=str(exc_type),
        error=exc_obj)


class ExceptionHandlingTests(unittest.TestCase):
    """Exception handling test cases"""

    def test_parse_exception_works(self):
        """Test parse_exception works"""
        try:
            print(1/0)
        except:
            print(parse_exception())


if __name__ == '__main__':
    unittest.main()
