"Check that functions can handle scalar input"

from numpy.testing import assert_array_almost_equal
import bottleneck as bn  # noqa
from .functions import reduce_functions, nonreduce_axis_functions


def unit_maker(func, func0, args=tuple()):
    "Test that bn.xxx gives the same output as bn.slow.xxx for scalar input."
    msg = '\nfunc %s | input %s\n'
    a = -9
    argsi = [a] + list(args)
    actual = func(*argsi)
    desired = func0(*argsi)
    err_msg = msg % (func.__name__, a)
    assert_array_almost_equal(actual, desired, err_msg=err_msg)


def test_scalar_input():
    "Test scalar input"
    funcs = reduce_functions() + nonreduce_axis_functions()
    for func in funcs:
        if func.__name__ not in ('partsort', 'argpartsort', 'push'):
            yield unit_maker, func, eval('bn.slow.%s' % func.__name__)
