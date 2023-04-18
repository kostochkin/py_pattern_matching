import typing as t


do_log = False  # For testing


def logged(name):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if do_log:
                _id = id(fn) % 100000
                print(f'-- [{_id}] [{name}] args: {args}, kwargs: {kwargs})')
                result = fn(*args, **kwargs)
                print(f'-- [{_id}] [{name}] --> {result}')
                return result
            else:
                return fn(*args, **kwargs)
        return wrapper
    return decorator


class Environment:

    class NotFound:
        pass

    def __init__(self, kv: dict):
        self._kv = kv

    def join(self, env):
        new_kv = {**self._kv, **env._kv}
        return Environment(new_kv)

    def lookup(self, key):
        return self._kv.get(key, self.NotFound)

    def to_dict(self):
        return {**self._kv}

    def __str__(self):
        args_str = str(self._kv)[1:-1]
        return f'Env({args_str})'

    def __repr__(self):
        return self.__str__()


def Env(**kv: dict) -> Environment:
    return Environment(kv)


class MatchResult:

    def __init__(self, matched, obj, value):
        self.matched = matched
        self.obj = obj
        self.value = value

    def __str__(self):
        val = self.value
        val = f"'{val}'" if isinstance(val, str) else val
        if self.matched:
            return f'<<{self.obj} = {val}>>'
        else:
            return f'<<{self.obj} /= {val}>>'
        return f'Pattern({self.matched}, {self.obj}: {val})'

    def __repr__(self):
        return self.__str__()


class Pattern:

    def __init__(self, pattern: t.Optional[t.Any] = None):
        self._pattern = pattern

    @logged('Match any')
    def __call__(self, obj: any) -> t.List[MatchResult]:
        return [MatchResult(True, self, obj)]

    def __str__(self):
        if self._pattern is None:
            return '_'
        return f'{self.__class__.__name__}({self._pattern})'

    def __repr__(self):
        return self.__str__()


class Named:

    name = None


class Var(Named, Pattern):

    def __init__(self, name):
        super().__init__(name)
        self.name = name

    @logged('Match var')
    def __call__(self, obj) -> t.List[MatchResult]:
        return [MatchResult(True, self, obj)]

    def __str__(self):
        return f'${self._pattern}'


class Value(Pattern):

    @logged('Match value')
    def __call__(self, obj) -> t.List[MatchResult]:
        matched = obj == self._pattern
        return [MatchResult(matched, self, obj)]

    def __str__(self):
        pat = self._pattern
        return f"'{pat}'" if isinstance(pat, str) else str(pat)


class List(Pattern):

    def __init__(self, *pattern):
        super().__init__(pattern)
        self._heads = []
        self._tail = None
        self._decompose_pattern()

    @logged('Match list')
    def __call__(self, obj) -> t.List[MatchResult]:
        if not isinstance(obj, list):
            return [MatchResult(False, self, obj)]

        return self._match_list(obj)

    def _match_list(self, _list):
        if len(_list) >= len(self._heads):
            matched_list = self._match_right_list(_list)
            return [MatchResult(True, self, _list)] + matched_list

        return [MatchResult(False, self, _list)]

    def _match_right_list(self, _list):
        result = []
        for element, value in zip(self._heads, _list):
            result.extend(element(value))

        if self._tail is not Ellipsis and self._tail is not None:
            result.extend(self._tail(_list[len(self._heads):]))

        return result

    def __len__(self):
        return len(self._pattern)

    def __str__(self):
        return f'[{self._pattern}]'

    def _decompose_pattern(self):
        for element in self._pattern:
            if self._tail is None:
                if element is Ellipsis:
                    self._tail = Ellipsis
                else:
                    self._heads.append(element)
            elif self._tail is Ellipsis and isinstance(element, Var):
                self._tail = element
            else:
                raise Exception("Wrong pattern")


class Tuple(Pattern):

    def __init__(self, *pattern):
        super().__init__(pattern)

    def __call__(self, obj) -> t.Tuple:
        if not isinstance(obj, tuple) or len(obj) != len(self._pattern):
            return [MatchResult(False, self, obj)]

        return [MatchResult(True, self, obj)] + self._match_tuple(obj)

    def _match_tuple(self, _tuple):
        return [
            result
            for element, value in zip(self._pattern, _tuple)
            for result in element(value)
        ]


class Dict(Pattern):

    def __init__(self, **pattern):
        self._pattern = pattern

    @logged('Match dict')
    def __call__(self, obj) -> t.List[MatchResult]:
        if not isinstance(obj, dict):
            return [MatchResult(False, self, obj)]

        return self._match_dict(obj)

    def _match_dict(self, _dict):
        matched_dict = self._match_it(_dict)
        return [MatchResult(True, self, _dict)] + matched_dict

    def _match_it(self, _dict):
        results = []
        for key, element in self._pattern.items():
            if key in _dict:
                results.extend(element(_dict[key]))
            else:
                results.append(MatchResult(False, self, ...))
        return results

    def __str__(self):
        kwargs = ', '.join([f'{k}={v}' for k, v in self._pattern.items()])
        return f'dict({kwargs})'


class Arg(Pattern):

    @logged('Match arg')
    def __call__(self, obj) -> [MatchResult]:
        env = Env()
        matched = True
        results = self._pattern(obj)
        for result in results:
            matched = matched and result.matched
            if isinstance(result.obj, Named):
                var_name = result.obj.name
                value = result.value
                old_value = env.lookup(var_name)
                if old_value != Environment.NotFound and old_value != value:
                    matched = False
                var_env = Env(**{var_name: value})
                env = env.join(var_env)
        return [MatchResult(matched, self, env)]


class Args(Arg):

    def __init__(self, *patterns: t.List[Pattern]):
        super().__init__(List(*patterns))


class Kwargs(Arg):

    def __init__(self, **patterns: t.Dict[str, Pattern]):
        super().__init__(Dict(**patterns))


class Dup(List):

    @logged('Match dup')
    def __call__(self, obj):
        return super().__call__([obj] * len(self._pattern))


class Obj(Dict):

    def __init__(self, obj_cls, **field_map):
        super().__init__(**field_map)
        self._obj_cls = obj_cls

    def __call__(self, obj):
        if not isinstance(obj, self._obj_cls):
            return [MatchResult(False, self, obj)]

        return self._match_obj_as_dict(obj)

    def _match_obj_as_dict(self, obj):
        obj_dict = {k: getattr(obj, k) for k in self._pattern}
        result = super().__call__(obj_dict)
        matched = result[0].matched
        return [MatchResult(matched, self, obj)] + result[1:]


def to_pattern(obj):
    if obj is Ellipsis:
        return Ellipsis
    if isinstance(obj, Pattern):
        return obj
    if isinstance(obj, list):
        return List(*map(to_pattern, obj))
    if isinstance(obj, tuple):
        return Tuple(*(map(to_pattern, obj)))
    if isinstance(obj, dict):
        return Dict(**{k: to_pattern(v) for k, v in obj.items()})
    return Value(obj)


# Synonyms
Any = Pattern
KW = Kwargs
Val = Value
