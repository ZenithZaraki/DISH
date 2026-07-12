from fastapi import APIRouter
from app.utils.command import command

router = APIRouter()

# @router.post("/ping")
@command
def ping(key: str, data: str = "pong"):
    return {"pong":data}

