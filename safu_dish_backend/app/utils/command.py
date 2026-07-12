from typing import Callable, Any, Dict
from inspect import get_annotations
from dataclasses_json import DataClassJsonMixin

def command(fun: Callable):
    def run(routing_key: str, payload: Dict[str, Any]):
        # get_annotations(fun)
        return fun(routing_key, **payload)
    return run

def json_return(fun: Callable[...,Dict[str,Any]|DataClassJsonMixin]):
    async def f(*a,**b):
        r = fun(*a,**b)
        if "__await__" in dir(r):
            r = await r
        if type(r) == dict:
            return r
        return r.to_dict()
    f.__annotations__ = fun.__annotations__
    return f

