import os
import sys
import json
from typing import Any, Dict, Optional, List, Set, Callable, Tuple
from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin
from dev.diagnostics import get_logger, terminal_alert

logger = get_logger("router")

@dataclass
class Command(DataClassJsonMixin):
    func: str
    exists: bool = False

@dataclass
class UIComponent(DataClassJsonMixin):
    type: str
    routing_key: str = "!"
    command_id: str = "!"
    attrs: Dict[str,str] = field(default_factory=dict)
    payload: Dict[str,Any] = field(default_factory=dict)

@dataclass
class UIGroup(DataClassJsonMixin):
    zone: str
    name: str
    components: List[UIComponent]

@dataclass
class UIManifest(DataClassJsonMixin):
    structure: List[UIGroup] = field(default_factory=list)
    commands: Dict[str,Command] = field(default_factory=dict)

    def routed_commands(self) -> List[UIComponent]:
        l = []
        for s in self.structure:
            l.extend(filter(lambda x: x.routing_key!="!", s.components))
        return l

def parse_manifest(file: str, name: str, module: Set[str]) -> UIManifest:
    obj: UIManifest = None
    try:
        with open(file,"r") as f:
            obj = UIManifest.from_dict(json.load(f))
    except:
        print(f"[ERROR] failed to load manifest file for {file}", file=sys.stderr)
        return UIManifest()
    for cmd in obj.commands.values():
        if cmd.func in module:
            cmd.exists = True
    for struct in obj.structure:
        for com in struct.components:
            if com.routing_key == "!":
                continue
            if com.routing_key[0] == '.':
                com.routing_key = f"{name}.{struct.zone}{com.routing_key}"
    return obj

