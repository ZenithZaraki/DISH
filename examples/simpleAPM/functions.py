

from safu_dish_backend.app.utils.command import command


@command
def echo(routing_key: str, value: str):
    return {"value":value}

## uncomment to use "altecho"
# @command
# def altecho(routing_key: str, value: int|float):
#     return {"value":str(value)}

