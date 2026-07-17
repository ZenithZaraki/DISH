from io import TextIOWrapper
from dataclasses import dataclass, field
import re
from typing import Callable, Iterable, Self, TypeVar
from os import path
import picl_types as ty

class Params:
    Matcher = Callable[[str],re.Match[str]|None]
    common_symbols = "a-zA-Z0-9_\\-"
    string_symbols = f"{common_symbols}$@#.:"

    def opfixed_value(preop: str = "", postop: str = "", prefix: str = "", postfix: str = "", symbols: str = common_symbols) -> Matcher:
        p1 = f"(?:{re.escape(preop)})?" if preop else ""
        p2 = f"(?:{re.escape(postop)})?" if postop else ""
        p3 = re.escape(prefix)
        p4 = re.escape(postfix)
        return re.compile(f'^{p1}{p3}[{symbols}]+{p4}{p2}$').match
    def fixed_value(prefix: str = "", postfix: str = "", symbols: str = string_symbols) -> Matcher:
        return Params.opfixed_value(prefix=prefix, postfix=postfix, symbols=symbols)
        # return re.compile(f'^{prefix}[{symbols}]+{postfix}$').match
    def fixed_string(prefix: str = "", postfix: str = "") -> Matcher:
        return Params.fixed_value('"'+prefix,postfix+'"')

    @classmethod
    def _init(cls):
        cls.VARIADIC = object()
        cls.string = cls.fixed_value('"', '"')
Params._init()

ParamSpec = tuple[Iterable[str]|str|Callable[[str],bool]|None]

@dataclass
class VariantSpec:
    """
    a specification of a constraint variant
    ident is the variant name
    paramspec is a list defining the acceptable parameters for that variant, each parameter specification may be list[str] for an enumerated list of accepted values, str for a single accepted value, Callable for simple checking, or None for manual checking of that parameter
    if paramspec is None, then no validation is done on the number or contents of the parameter list

    paramspec may also be a set of paramspecs, in which case validation fails only if no spec matches
    """
    ident: str
    paramspec: list[ParamSpec|None] | ParamSpec | None = field(default_factory=tuple)

@dataclass
class Contract:
    definitions: dict[str,ty.PType] = field(default_factory=dict)
    constraints: dict[str,list["Constraint"]] = field(default_factory=dict)
    sequence: list["Constraint"] = field(default_factory=list)
    primary_key: str = None
    primary_key_type: str = None
    type_gen: Callable[[list[ty.PType]],ty.PType] = None

    def activate(self) -> None:
        for c in self.sequence:
            c.activate()

    def add_constraint(self, variant: str, args: list[str]) -> None:
        c = Constraint.instance(variant, self, self.definitions, args)
        self.sequence.append(c)
        cn = type(c).__name__
        if cn in self.constraints.keys():
            self.constraints[cn].append(c)
        else:
            self.constraints[cn] = [c]
    
    def firstof(self, ctype: type["Constraint"]) -> int:
        for i in range(len(self.sequence)):
            if isinstance(self.sequence[i], ctype):
                return i
        return -1
    def lastof(self, ctype: type["Constraint"]) -> int:
        for i in reversed(range(len(self.sequence))):
            if isinstance(self.sequence[i], ctype):
                return i
        return -1

class Constraint:
    registry: dict[str,type[Self]] = {}
    mandatory: set[type[Self]] = set()
    variants: list[VariantSpec] = []
    default: type[Self] = None

    def __init__(self, variant: str, contract: Contract, definitions: dict[str,Contract], args: list[str] = None, /, inexpansion: bool = False) -> None:
        self._variant = variant
        self._contract = contract
        self._definitions = definitions
        self._args = args or []
        self._matched_params: int | None = None
        if not (inexpansion or self.validate_state()):
            raise ValueError(f"invalid state ({type(self).__name__}) ({variant})")
    
    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._variant},{self._args})"

    def instance(constraint: str, *args) -> Self:
        """creates an instance of the given constraint with the provided args"""
        return Constraint.registry.get(constraint, Constraint.default)(constraint, *args)
    
    def validate_state(self) -> bool:
        """validates a newly constructed constraint instance to check for obvious defects"""
        return True
    
    def activate(self) -> None:
        """performs any final processing that must be done after all @uses constraints are resolved"""
        return None

X = TypeVar('X', bound=Constraint)
def constraintclass(cls: type[X] = None, /, mandatory: bool = False) -> type[X]:
    def inner(cls: type[X]) -> type[X]:
        for variant in cls.variants:
            if variant.ident in Constraint.registry.keys():
                raise NameError("multiple constraints using same variant key")
            Constraint.registry[variant.ident] = cls
        if mandatory:
            Constraint.mandatory.add(cls)
        validate_state = cls.validate_state
        def var_validate(self: X):
            if not validate_state(self):
                # print("cls validate_state failure")
                return False
            for variant in cls.variants:
                if variant.ident == self._variant:
                    # print(variant.ident)
                    if variant.paramspec is None:
                        return True
                    def inner_validate(paramspec: ParamSpec, marker: int | None = None) -> bool:
                        args = self._args
                        if len(paramspec) and paramspec[-1] == Params.VARIADIC:
                            paramspec = paramspec[:-1]
                            args = args[:len(paramspec)]
                        if len(paramspec) != len(args):
                            return False
                        for arg, param in zip(args, paramspec):
                            if param is None:
                                continue
                            if type(param) == str:
                                if param == arg:
                                    continue
                                return False
                            if hasattr(param, "__contains__"):
                                if arg in param:
                                    continue
                                return False
                            if callable(param):
                                if param(arg):
                                    continue
                                # print(param, arg)
                                return False
                            return False
                        self._matched_params = marker
                        return True
                    if type(variant.paramspec) == list:
                        return any(inner_validate(x, m) for m, x in enumerate(variant.paramspec))
                    return inner_validate(variant.paramspec)
            return False
        cls.validate_state = var_validate
        return cls
    r = inner(cls) if cls else inner
    # print(f"cls={cls} returning {r}")
    return r

class DefConstraint(Constraint):
    """A constraint that defines something"""
    pass

class TestConstraint(Constraint):
    """A constraint that validates the contract against a function"""
    
    def validate(self, func: Callable) -> bool:
        raise NotImplementedError()

class MetaConstraint(Constraint):
    """A constraint that validates the contract itself"""
    
    def validate(self) -> bool:
        raise NotImplementedError()

class UniqueConstraint(MetaConstraint):
    """A constraint that validates that there is exactly one instance of itself in the contract"""
    
    def validate(self):
        # return sum(len(self._contract.constraints.get(variant, [])) for variant in type(self).variants) == 1
        return len(self._contract.constraints.get(type(self).__name__, [])) <= 1

@constraintclass(mandatory=True)
class PrimaryKeyConstraint(UniqueConstraint):
    """The constraint specifying the primary key this contract is identified with"""
    variants = [
        VariantSpec("@ident", (Params.string,)),
        VariantSpec("@definition", (Params.string,))
    ]
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._contract.primary_key_type = self._variant
        self._contract.primary_key = self._args[0][1:-1]
    
    def validate_state(self):
        if self._variant == "@ident":
            return self._contract.sequence[-1]._variant == "@type"
        elif self._variant == "@definition":
            return self._contract.sequence[-1]._variant == "@internal"
        return False

@constraintclass(mandatory=True)
class ContractFeatureConstraint(UniqueConstraint):
    """The constraint indicating what feature the contract is using (required, optional, internal)"""
    variants = [
        VariantSpec("@required"),
        VariantSpec("@internal"),
        VariantSpec("@optional", (Params.string,))
    ]

@constraintclass
class BoundAsConstraint(UniqueConstraint):
    """The constraint defining the frontend handle to bind the resource to"""
    variants = [
        VariantSpec("@boundas", (Params.string,))
    ]

@constraintclass
class TypeConstraint(UniqueConstraint):
    """The constraint that indicates the type of the contract"""
    variants = [
        VariantSpec("@type", (Params.string,))
    ]

    def validate_state(self):
        if self._contract.sequence[-1]._variant == "@definition":
            return self._args[0][1:-1] in ("type", "macro")
        elif self._contract.sequence[-1]._variant in ("@required", "@optional"):
            return True
        return False
    
    @property
    def name(self) -> str:
        return self._args[0][1:-1]

@constraintclass
class UsesConstraint(DefConstraint):
    """The constraint that indicates what internal definitions are used in this contract"""
    variants = [
        VariantSpec("@uses", [(Params.string,Params.VARIADIC)])
    ]

    def validate_state(self):
        return self._contract.sequence[-1]._variant in ("@uses", "@type" if self._contract.sequence[0]._variant == "@internal" else "@boundas")
    
    @property
    def symbol(self) -> str:
        if self._matched_params == 0:
            return self._args[0][1:-1]
        raise ValueError(f"invalid _matched_parms ({self._matched_params})")

@constraintclass
class FlagConstraint(DefConstraint):
    """The constraint that defines a flag"""
    variants = [
        VariantSpec("@flag", [(Params.fixed_string('$'),"(PIXL)",Params.fixed_string('@'),'=',Params.opfixed_value('#',symbols=Params.common_symbols+':'))])
    ]

@constraintclass
class ParamConstraint(DefConstraint):
    """The constraint that defines a parameter"""
    variants = [
        VariantSpec("@param", [
            (Params.fixed_value('(',')',Params.common_symbols),("[str]",),Params.fixed_value('"#','"',Params.common_symbols)),
            (Params.fixed_value('[',']',"A-Z"))
        ])
    ]

    @property
    def binding_symbol(self) -> str:
        match self._matched_params:
            case 0:
                return self._args[2][2:-1]
            case 1:
                return self._args[0][1:-1]
            case _:
                raise ValueError(f"invalid _matched_params ({self._matched_params})")
    @property
    def binding_param(self) -> str:
        match self._matched_params:
            case 0 | 1:
                return self._args[0][1:-1]
            case _:
                raise ValueError(f"invalid _matched_params ({self._matched_params})")

@constraintclass
class ExpandsConstraint(DefConstraint):
    """The constraint that defines macro and type expansion"""
    variants = [
        VariantSpec("@expands", None)
    ]
    def validate_state(self):
        if self._contract.constraints["TypeConstraint"][0].name == "type":
            return Params.fixed_value('{','}',"A-Za-z_<>?")(''.join(self._args))
        return True

@constraintclass
class SignatureConstraint(TestConstraint):
    """The constraint that defines a type signature"""
    variants = [
        VariantSpec("@signature", [
            (Params.fixed_value('(',')',Params.common_symbols),Params.fixed_value('["$','"]',Params.common_symbols),Params.VARIADIC),
            (Params.VARIADIC,)
        ])
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        i = 0 if self._matched_params else 2
        self._type = ''.join(self._args[i:])
        if self._type[0] == '(':
            self._type = self._type[1:-1].split("->")
    
    def activate(self) -> None:
        if type(self._type) == str:
            self._type = ty.parse_type(self._type, self._contract.definitions)
        elif type(self._type) == list:
            self._type = [ty.parse_type(x, self._contract.definitions) for x in self._type]

class PlaceholderConstraint(DefConstraint):
    """Debugging placeholder for unimplemented constraints"""

Constraint.default = PlaceholderConstraint

class PICL:
    def __init__(self, f: str | TextIOWrapper) -> None:
        self.contracts: dict[str,Contract] = {}
        self.definitions: dict[str,Contract] = {}
        lines: list[str] = None
        if type(f) == str:
            lines = f.splitlines()
        else:
            lines = f.readlines()
        contractDepth = 0
        curr = None
        expand = None
        for line in map(str.strip, lines):
            if not len(line):
                continue
            if line[0] == "%":
                continue
            if line[0] == "{" or line[-1] == "{":
                if contractDepth == 0:
                    curr = Contract()
                elif line[0] == "{" or contractDepth == 2:
                    raise SyntaxError("nested contracts not allowed")
                elif line.startswith("@expands"):
                    expand = []
                contractDepth += 1
                continue
            if line[0] == "}":
                contractDepth -= 1
                if contractDepth == 0:
                    d = None
                    if curr.primary_key_type == "@ident":
                        d = self.contracts
                    elif curr.primary_key_type == "@definition":
                        d = self.definitions
                    if d is None:
                        raise SyntaxError("contract has no name or ident")
                    d[curr.primary_key] = curr
                    curr = None
                elif contractDepth == 1:
                    curr.add_constraint("@expands", expand)
                    expand = None
                continue
            if contractDepth == 0:
                continue
            tokens = line.split()
            if expand is None:
                curr.add_constraint(tokens[0], tokens[1:])
            else:
                expand.append(tokens)
        processable = set()
        completed = set()
        while True:
            for k, v in self.definitions.items():
                if k in completed:
                    continue
                if "UsesConstraint" in v.constraints:
                    if all(x.symbol in completed for x in v.constraints["UsesContraint"]):
                        processable.add(k)
                        continue
                else:
                    processable.add(k)
            if not len(processable):
                break
            for k in processable:
                c = self.definitions[k]
                self._expand_uses(c)
                self._create_typegen(c)
                c.activate()
            completed |= processable
            processable.clear()
        for k, v in self.contracts.items():
            if "UsesConstraint" in v.constraints:
                self._expand_uses(v)
            v.activate()
    def _create_typegen(self, contract: Contract) -> None:
        # print("typegen for:", contract, sep='\n')
        params = []
        for c in contract.sequence:
            # print(c)
            if isinstance(c, ParamConstraint):
                # print(f"binding parameter: {c.binding_symbol}")
                params.append(c.binding_symbol)
            if isinstance(c, SignatureConstraint):
                # print("creating type generator")
                spec = ty.InstancingSpec(c._type, params, contract.definitions)
                # print(spec)
                contract.type_gen = ty.create_type(spec)
                break
    def _expand_uses(self, contract: Contract) -> None:
        if "UsesConstraint" not in contract.constraints:
            return
        p = contract.firstof(UsesConstraint)
        uc = len(contract.constraints["UsesConstraint"])
        excised = contract.sequence[p:]
        contract.sequence = contract.sequence[:p]
        for i in range(uc):
            use = excised[i]
            resolved = self._resolve_uses(use)
            if any(x[0] == "@uses" for x in resolved[0]):
                raise SyntaxError("@expands must not resolve to a @uses constraint")
            contract.definitions |= resolved[1]
            for c in resolved[0]:
                contract.add_constraint(c[0], c[1:])
        contract.sequence.extend(excised[uc:])
        del contract.constraints["UsesConstraint"]
    def _resolve_uses(self, uses: UsesConstraint) -> tuple[list[list[str]],dict[str,ty.PType]]:
        defc: Contract = self.definitions[uses.symbol]
        t: TypeConstraint = defc.constraints["TypeConstraint"][0]
        if t.name == "type":
            if len(uses._args) > 1:
                raise SyntaxError("type definitions do not take parameters from @uses")
            return ([],dict([(defc.primary_key,defc.type_gen)]))
        elif t.name == "macro":
            raise NotImplementedError("per the current spec definitions of type \"macro\" have not been implemented")
        else:
            raise SyntaxError(f"invalid definition type ({t.name})")


expath = path.join(path.dirname(path.dirname(path.dirname(path.dirname(__file__)))), "examples", "simpleAPM", "ui", "interface.picl")

if __name__ == "__main__":
    with open(expath, "r") as f:
        pic = PICL(f)

