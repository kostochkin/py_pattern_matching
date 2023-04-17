import pytest

import pattern_matching.patterns
from pattern_matching.cases import def_match, Cases
from pattern_matching.patterns import Var, Any


pattern_matching.patterns.do_log = True


def test_simple_case():

    @def_match(1, 2, 3)
    def fn():
        return True

    assert fn(1, 2, 3)


def test_assign_var():

    @def_match(Var('should_be_assigned'))
    def fn(should_be_assigned):
        return should_be_assigned

    assert fn(5) == 5


def test_deep_decompose():

    @def_match([1, 2, [Var('x')], {'a': (False, Var('y'))}])
    def fn(x, y):
        return x + y

    assert fn([1, 2, ['tr'], {'a': (False, 'ue!')}]) == 'true!'


def test_select_case():

    @def_match(True)
    def fn():
        return 'a'

    @def_match(False)
    def fn():
        return 'b'

    assert fn(True) == 'a'
    assert fn(False) == 'b'


def test_select_default_case():

    @def_match(True)
    def fn():
        return 'a'

    with pytest.raises(Cases.NonExhaustivePatterns):
        fn(None)


def test_case_class():
    class A:

        result = True
        a = 5

        @def_match(Var('self'), 1, 2, 3)
        def fn(self):
            return self.result

        @def_match(Var('self'), Var('x'))
        def fn(self, x):
            return self.a + x

    assert A().fn(1, 2, 3) is True
    assert A().fn(10) == 15
