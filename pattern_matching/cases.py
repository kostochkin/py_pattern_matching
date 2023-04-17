import typing as t

from .patterns import Args, Arg, Pattern, to_pattern


class Cases:

    cases = {}

    class NonExhaustivePatterns(Exception):
        pass

    def append(self, name: str, fn: callable, pattern: Arg):
        default = Args(Pattern())
        cases = self.cases.setdefault(name, [(self._default(name), default)])
        cases.insert(0, (fn, pattern))

    def select(self, name, combined_arg) -> t.Tuple[callable, dict]:
        for fn, pattern in self.cases[name]:
            result = pattern(combined_arg)[0]
            if result.matched:
                return fn, result.value.to_dict()
        raise Exception('Programming error')

    def _default(self, name):
        def wrapper(*args, **kwargs):
            args_str = ', '.join(map(str, args))
            kwargs_str = ', '.join([f'{k}={v}' for k, v in kwargs.items()])
            full_args = ', '.join([args_str, kwargs_str])
            message = f'{name}({full_args})'
            raise self.NonExhaustivePatterns(message)
        return wrapper


_cases = Cases()


def def_match(*pat_args, **pat_kwargs):
    pattern = Args(to_pattern(pat_args), to_pattern(pat_kwargs))

    def decorator(fn):
        fn_name = f'{fn.__module__}::{fn.__qualname__}'
        _cases.append(fn_name, fn, pattern)

        def wrapper(*args, **kwargs):
            fn, fn_kwargs = _cases.select(fn_name, [args, kwargs])
            return fn(**fn_kwargs)
        return wrapper

    return decorator
