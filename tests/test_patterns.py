import pytest

import pattern_matching.patterns
from pattern_matching.patterns import (
    List,
    Var,
    Dict,
    Val,
    Dup,
    Arg,
    Args,
    Tuple,
    Obj,
)


pattern_matching.patterns.do_log = True


@pytest.mark.parametrize('value', ['aaa', 123, True, {1: 2}])
def test_var_match(value):
    assert Var('a')(value)[0].matched is True


@pytest.mark.parametrize('expected,given,matched', [
    (1, 1, True),
    (2, 1, False),
    ('a', 'a', True),
    ('b', 'a', False),
])
def test_value_match(expected, given, matched):
    assert Val(expected)(given)[0].matched is matched


@pytest.mark.parametrize('pattern,given,matched', [
    ([], [], True),
    ([], {}, False),
    ([Var('a')], [], False),
    ([Val(1)], [2], True),
    ([Val(1)], [1], True),
    ([Val(1), Var('b')], [1, 2], True),
    ([Val(1), ...], [1], True),
    ([Val(1), ...], [1, 2], True),
    ([Val(1), ..., Var('b')], [1, 2, 3], True),
])
def test_list_match(pattern, given, matched):
    matched_result = List(*pattern)(given)
    assert matched_result[0].matched is matched


@pytest.mark.parametrize('pattern,given,matched', [
    ({}, {}, True),
    ({}, [], False),
    ({'a': Var('b')}, {'a': 1}, True),
    ({'a': Var('b')}, {}, False),
    ({'a': Val(1)}, {'a': 1}, True),
    ({'b': Val(1)}, {'a': 1}, False),
])
def test_dict_match(pattern, given, matched):
    matched_args = Dict(**pattern)(given)
    all_matched = all([x.matched for x in matched_args])
    assert all_matched is matched


@pytest.mark.parametrize('pattern,given,matched,result', [
    (Dict(), {}, True, {}),
    (Dict(), [], False, {}),
    (Dict(a=Var('b')), {'a': 1}, True, {'b': 1}),
    (Dict(a=Var('b')), {}, False, {}),
    (Dict(a=Val(1)), {'a': 1}, True, {}),
    (Dict(b=Val(1)), {'a': 1}, False, {}),
    (List(Val(1), Var('a')), [1, 10], True, {'a': 10}),
    (List(Val(1), Val(1)), [1, 10], False, {}),
    (List(
        Val(1),
        Dict(a=Var('o'))),
     [1, {'a': 10}], True, {'o': 10}),
    (List(Var('a'), Var('a')), [1, 1], True, {'a': 1}),
    (List(Var('a'), Var('a')), [1, 2], False, {'a': 1}),
    (List(Var('a'), ..., Var('b')),
     [1, 'a', True], True, {'a': 1, 'b': ['a', True]}),
])
def test_arg_match(pattern, given, matched, result):
    matched_arg = Arg(pattern)(given)[0]
    assert matched_arg.matched is matched
    if matched:
        env = matched_arg.value.to_dict()
        assert env == result


@pytest.mark.parametrize('pattern,given,matched,result', [
    ([Var('a'), Var('a')], [1, 1], True, {'a': 1}),
    ([Var('a'), Var('a')], [1, 2], False, {}),
])
def test_args_match(pattern, given, matched, result):
    matched_arg = Args(*pattern)(given)[0]
    assert matched_arg.matched is matched
    if matched:
        env = matched_arg.value.to_dict()
        assert env == result, matched_arg


@pytest.mark.parametrize('pattern,given,matched', [
    ([Val(1), Var('a')], 1, True),
    ([Val('1'), Var('a')], '2', False),
])
def test_dup_match(pattern, given, matched):
    matched_args = Dup(*pattern)(given)
    all_matched = all([x.matched for x in matched_args])
    assert all_matched is matched


@pytest.mark.parametrize('pattern,given,matched', [
    ((Val(1), Val(2), Val(3)), (1, 2, 3), True),
    ((Val(1), Val(2), Val(3)), (1, 2), False),
    ((Val(1), Val(2)), (1, 2, 3), False),
    ((Var('x'), Val(2), Val(3)), (1, 2, 3), True),
])
def test_tuple_match(pattern, given, matched):
    result = Tuple(*pattern)(given)
    assert result[0].matched is matched


@pytest.mark.parametrize('x,y,z,matched', [
    (1, 2, 3, True),
    (1, 5, 3, False),
])
def test_obj_match(x, y, z, matched):
    class Foo:
        x = 1
        y = 2
        z = 3

    obj = Foo()
    pattern = Obj(Foo, x=Val(x), y=Val(y), z=Val(z))
    assert pattern(obj)[0].matched is True


@pytest.mark.parametrize('x,y,matched', [
    (1, 2, True),
    (1, 5, False),
])
def test_obj_partial_match(x, y, matched):
    class Foo:
        x = 1
        y = 2
        z = 3

    obj = Foo()
    pattern = Obj(Foo, x=Val(x), y=Val(y))
    assert pattern(obj)[0].matched is True


def test_obj_var_match():
    class Foo:
        x = 1
        y = 2
        z = 3

    obj = Foo()
    pattern = Arg(Obj(Foo, x=Val(1), y=Var('z')))
    assert pattern(obj)[0].value.lookup('z') == 2


# End
