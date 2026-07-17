"""
this module handles parsing of PICL types
"""

from typing import Callable, Self, TypeVar
from dataclasses import dataclass

class PType:
    name: str

    def __init__(self, params: list[Self]) -> None:
        pass
    def __repr__(self) -> str:
        return type(self).__name__
    def __str__(self):
        return repr(self)

@dataclass
class InstancingSpec:
    full: str
    param_defs: list[str]
    embedded_defs: dict[str,PType]

class Pnoparams(PType):
    def __init__(self, params: list[PType]) -> None:
        # print(params)
        if len(params):
            raise ValueError(f"PType {type(self).__name__} takes no parameters")
    def __eq__(self, other) -> bool:
        if type(other) == Pany:
            return True
        return type(self) == type(other)

class Pfixedparams(PType):
    count: int
    def __init__(self, params: list[PType]):
        super().__init__(params)
        if self.count and len(params) != self.count:
            raise ValueError(f"PType {type(self).__name__} takes exactly {self.count} parameters")
        self.params = params
    def __eq__(self, other: Self) -> bool:
        if type(other) == Pany:
            return True
        if type(self) != type(other):
            return False
        return self.params == other.params
    def __repr__(self) -> str:
        return f"{type(self).__name__}<{','.join(map(str,self.params))}>"

class Pstr(Pnoparams):
    name = "str"
class Pint(Pnoparams):
    name = "int"
class Pfloat(Pnoparams):
    name = "float"
class Pbool(Pnoparams):
    name = "bool"
class Pnull(Pnoparams):
    name = "null"
class Pany(Pnoparams):
    name = "any"
    def __eq__(self, other: Self) -> bool:
        return isinstance(other, PType)

class Poptional(Pfixedparams):
    count = 1
    name = "optional"
class Pmap(Pfixedparams):
    count = 2
    name = "map"
class Parray(Pfixedparams):
    count = 1
    name = "array"
class Ptuple(Pfixedparams):
    count = None
    name = "tuple"

class Punion(Pfixedparams):
    count = None
    name = "union"
    def __init__(self, params):
        super().__init__(params)
        if not len(params):
            raise ValueError("Punion requires at least one parameter")
        if any(isinstance(p, Poptional) for p in params):
            raise ValueError("Punion may not have optional variants")
        self.params = params
    def __eq__(self, other: Self) -> bool:
        if type(other) == Pany:
            return True
        if type(self) != type(other):
            return False
        if len(self.params) != len(other.params):
            return False
        return all(x in other.params for x in self.params)
class Poneof(Pfixedparams):
    count = None
    name = "oneof"
    def __init__(self, params):
        super().__init__(params)
        if not len(params):
            raise ValueError("Poneof requires at least one parameter")
        self.params = params
    def __eq__(self, other: Self) -> bool:
        if type(other) == Pany:
            return True
        if type(other) in (Punion,Poneof):
            return all(x in self.params for x in other.params)
        return other in self.params

class Precord(PType):
    name = "record"
    def __init__(self, params: dict[str,PType]):
        super().__init__(params)
        self.params = params
    def __eq__(self, other: Self) -> bool:
        if type(other) == Pany:
            return True
        if type(other) != type(self):
            return False
        return self.params == other.params
    def __repr__(self) -> str:
        return 'Precord<{'+','.join([f"{k}:{v}"for(k,v)in self.params.items()])+'}>'

PTReg = dict[str,PType]

_builtin_types: PTReg = {
    "str":Pstr,
    "int":Pint,
    "float":Pfloat,
    "bool":Pbool,
    "null":Pnull,
    "any":Pany,
    "optional":Poptional,
    "union":Punion,
    "oneof":Poneof,
    "map":Pmap,
    "array":Parray,
    "tuple":Ptuple
}

def parse_type(string: str, typedefs: PTReg = None) -> PType:
    reg = _builtin_types | (typedefs or {})
    string = ''.join(string.split())
    def parse_single(string: str) -> PType:
        i = 0
        state = 0
        depth = [0,0]
        start = 0
        markers = []
        cmarkers = []
        while i < len(string):
            if state == 0 and string[i] == "?":
                break
            if depth[0] + depth[1] == 1:
                if string[i] == ",":
                    markers.append(i)
                elif state == 1 and string[i] == ":":
                    cmarkers.append(i)
            if string[i] == "{":
                depth[0] += 1
                if not state:
                    start = i
                    state = 1
            elif string[i] == "<":
                depth[1] += 1
                if not state:
                    start = i
                    state = 2
            elif string[i] == "}":
                depth[0] -= 1
                if state == 1 and depth[0] == 0:
                    break
            elif string[i] == ">":
                depth[1] -= 1
                if state == 2 and depth[1] == 0:
                    break
            i += 1
        markers.append(i)
        r = None
        # print(state)
        if state == 0:
            r = reg[string[:i]]([])
        elif state == 1:
            # print(markers, cmarkers)
            zl = list(zip(zip([start+1]+[x+1 for x in markers[:-1]],cmarkers),zip([x+1 for x in cmarkers],markers)))
            # print(zl)
            # print([(string[k[0]:k[1]],string[v[0]:v[1]])for(k,v)in zl])
            d = {string[k[0]:k[1]]: parse_single(string[v[0]:v[1]]) for (k,v) in zl}
            # print(d)
            r = Precord(d)
        elif state == 2:
            l = [parse_single(string[a:b]) for (a,b) in zip([start+1]+[x+1 for x in markers[:-1]],markers)]
            # print(l)
            r = reg[string[:start]](l)
        # print(len(string), i)
        if string[-1] == "?":
            return Poptional([r])
        return r
    return parse_single(string)

def create_type(spec: InstancingSpec) -> Callable[[list[PType]],PType]:
    def _ANON_CREATED_TYPE(params: list[PType]):
        local_reg = dict(zip(spec.param_defs, params))
        return parse_type(spec.full, spec.embedded_defs | local_reg)
    return _ANON_CREATED_TYPE


# class PType:
#     registry: dict[str,type[Self]] = {}
#     default: type[Self] = None
#     tname: str = None

#     def __init__(self, name: str, params: list[Self]):
#         self.name = name
#         self.params = params

#     def instance(name: str, *args) -> Self:
#         return PType.registry.get(name, PType.default)(name, *args)

# X = TypeVar('X', bound=PType)
# def ptypeclass(cls: type[X]) -> type[X]:
#     PType.registry[cls.tname] = cls
#     return cls

# @ptypeclass
# class Pstr(PType):
#     tname = "str"


