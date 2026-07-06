# router.py — diagnostics-integrated
import os
import re
import sys
import json
import asyncio
import inspect
import importlib
import traceback
import importlib.util
from typing import Any, Dict
from pydantic import BaseModel
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request
from dev.diagnostics import get_logger, terminal_alert

logger = get_logger("router")
terminal_alert("[>] DISH Router initialized...", level="INFO")
terminal_alert(f"[>] ROUTER using Python from: {sys.executable}", level="INFO")

BOOTSTATE_PATH = os.path.join( "app", "config", "bootstate.json")
COMPONENT_MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "component_manifest.json"))

def update_bootstate(key: str, value: bool):
    """
    Embedded function — updates only the given key in app/config/bootstate.json
    without overwriting other keys.
    """
    # Load existing state
    if os.path.exists(BOOTSTATE_PATH):
        try:
            with open(BOOTSTATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except json.JSONDecodeError:
            state = {}
    else:
        state = {}

    # Update only the specified key
    state[key] = value

    # Write back updated state
    with open(BOOTSTATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

try:
    with open(COMPONENT_MANIFEST_PATH, "r") as f:
        component_manifest = json.load(f)
        VALID_COMPONENT_TYPES = set(component_manifest.keys())
        logger.info("COMPONENT_MANIFEST_LOAD | Loaded component_manifest.json")
except Exception as e:
    terminal_alert(f"Failed to load component_manifest.json: {e}", level="ERROR")
    logger.error(f"COMPONENT_MANIFEST_LOAD_FAIL | {e}")
    component_manifest = {}
    VALID_COMPONENT_TYPES = set()

router = APIRouter()

def serialize_command_map(cmd_map: dict) -> dict:
    """Convert command_map with function objects into JSON-safe metadata."""
    safe_map = {}
    for key, func in cmd_map.items():
        safe_map[key] = {
            "callable": callable(func),
            "func_name": getattr(func, "__name__", None),
            "module": getattr(func, "__module__", None)
        }
    return safe_map

def safe_import(module_name: str, package: str = None):
    try:
        return importlib.import_module(module_name, package=package)
    except Exception as e:
        terminal_alert(f"Could not import {module_name}: {e}", level="WARNING")
        logger.warning(f"IMPORT_FAIL | {module_name} | {e}")
        return None

def discover_modules(root_dir):
    modules = []
    try:
        for name in os.listdir(root_dir):
            mod_path = os.path.join(root_dir, name)
            if os.path.isdir(mod_path):
                func_path = os.path.join(mod_path, "functions.py")
                if os.path.exists(func_path):
                    modules.append((func_path, name))
        logger.info(f"DISCOVER_MODULES | Found {len(modules)} modules under {root_dir}")
    except Exception as e:
        terminal_alert(f"Module discovery failed: {e}", level="ERROR")
        logger.error(f"DISCOVER_MODULES_FAIL | {e}")
    return modules

MODULE_ROOT = os.path.join(os.path.dirname(__file__), "modules")
discovered_modules = discover_modules(MODULE_ROOT)

class CommandRequest(BaseModel):
    command: str
    value: Dict[str, Any] = {}

# --- REGEX Patterns ---
FUNC_PATTERN = re.compile(r"^(?:async\s+)?def\s+(\w+)\(")
UI_MARKER_PATTERN = re.compile(r"#\s*@ui\s+(.*)")
UI_GROUP_PATTERN = re.compile(r"#\s*@ui_group\s+\"(.+?)\"")
UI_ZONE_PATTERN = re.compile(r'#\s*@ui_zone\s+"?([\w\.\-]+)"?')
# --- UI Marker Parser ---
def parse_ui_marker(line):
    for component_type in VALID_COMPONENT_TYPES:
        if component_type in line:
            config = {"type": component_type}

            # Capture standard attributes: name="...", text="...", etc.
            for attr, val in re.findall(r'(\w+)="(.*?)"', line):
                if attr != component_type:
                    config[attr] = val

            # Capture list-type attributes: values=[...], filetypes=[...]
            for attr, list_val in re.findall(r'(\w+)=\[(.*?)\]', line):
                config[attr] = [v.strip().strip('"') for v in list_val.split(",")]

            return config
    return None

# --- Manifest Builder ---
def scan_file(filepath, module_name):
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except Exception as e:
        terminal_alert(f"Failed to read {filepath}: {e}", level="ERROR")
        logger.error(f"SCAN_FILE_IO_FAIL | {filepath} | {e}")
        return {}

    active_zone = "main"
    group = None
    ui_stack = []
    interface_data = defaultdict(dict)
    module_funcs = set()

    # --- Pre-import: ping check ---
    module_file = os.path.splitext(os.path.basename(filepath))[0]
    try:
        module = safe_import(f"app.modules.{module_name}.{module_file}")
        module_funcs = set(dir(module)) if module else set()
        logger.debug(f"SCAN_FILE_IMPORT | Imported app.modules.{module_name}.{module_file}")
    except Exception as e:
        terminal_alert(f"Error importing app.modules.{module_name}.{module_file}: {e}", level="WARNING")
        logger.warning(f"SCAN_FILE_IMPORT_FAIL | {module_name}.{module_file} | {e}")
        module = None

    def assign_unique_keys(controls, base_key):
        return [{**ctrl, "routing_key": f"{base_key}.{i}"} for i, ctrl in enumerate(controls)]

    for line in lines:
        zone_match = UI_ZONE_PATTERN.search(line)
        group_match = UI_GROUP_PATTERN.search(line)
        marker_match = UI_MARKER_PATTERN.search(line)
        func_match = FUNC_PATTERN.match(line)

        # Static controls not tied to a function
        if (zone_match or group_match) and ui_stack:
            controls = [parse_ui_marker(u) for u in ui_stack if parse_ui_marker(u)]
            if controls:
                keyed_controls = assign_unique_keys(controls, f"{module_name}.{active_zone}.__static__")
                interface_data[active_zone]["__static__"] = {
                    "group": group,
                    "controls": keyed_controls
                }
            ui_stack = []
            group = None

        if zone_match:
            active_zone = zone_match.group(1).strip()
            continue
        if group_match:
            group = group_match.group(1).strip()
            continue
        if marker_match:
            ui_stack.append(marker_match.group(1).strip())
            continue
        if func_match:
            func_name = func_match.group(1).strip()
            base_key = f"{module_name}.{active_zone}.{func_name}"
            controls = [parse_ui_marker(u) for u in ui_stack if parse_ui_marker(u)]
            ui_stack = []
            if controls:
                valid = func_name in module_funcs
                keyed_controls = assign_unique_keys(controls, base_key)
                interface_data[active_zone][func_name] = {
                    "group": group,
                    "controls": keyed_controls,
                    "routing_key": base_key,
                    "ping": valid
                }
            group = None

    # Final unprocessed stack
    if ui_stack:
        controls = [parse_ui_marker(u) for u in ui_stack if parse_ui_marker(u)]
        if controls:
            keyed_controls = assign_unique_keys(controls, f"{module_name}.{active_zone}.__static__")
            interface_data[active_zone]["__static__"] = {
                "group": group,
                "controls": keyed_controls
            }

    logger.debug(f"SCAN_FILE_DONE | {module_name} -> zones={list(interface_data.keys())}")
    return interface_data

# --- Command Mapping ---
def generate_command_map(interface_data, module_path, module_name):
    command_map = {}

    try:
        spec = importlib.util.spec_from_file_location(f"{module_name}.functions", module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        logger.info(f"[+] MODULE IMPORTED] {module_name}.functions")
    except Exception as e:
        logger.exception(f"[X] MODULE IMPORT FAILED] {module_name}: {e}")
        return {}

    for zone, funcs in interface_data.items():
        for func_key, entry in funcs.items():
            if func_key == "__static__":
                continue

            base_routing_key = entry.get("routing_key")
            func = getattr(mod, func_key, None)

            if not func:
                logger.warning(f"[!] '{func_key}' not found in {module_name}.functions")

                # Fallback: Try parent routing function ONLY if callable
                fallback_func = command_map.get(base_routing_key)
                if callable(fallback_func):
                    func = fallback_func
                    logger.info(f"[~] Using fallback function from '{base_routing_key}' for control mapping.")
                else:
                    logger.error(f"[X] No valid callable fallback for '{func_key}' via '{base_routing_key}'")
                    continue  # Skip this function mapping

            # Map the top-level routing key
            if base_routing_key:
                if base_routing_key in command_map:
                    logger.warning(f"[X] DUPLICATE ROUTING KEY] {base_routing_key} already mapped; skipping {func_key}")
                else:
                    command_map[base_routing_key] = func
                    logger.info(f"[+] MAPPED] {base_routing_key} -> {func_key}()")

            # Map each control-level routing key
            controls = entry.get("controls", [])
            for control in controls:
                control_rk = control.get("routing_key")
                if not control_rk:
                    logger.warning(f"[!] CONTROL WITHOUT ROUTING KEY] under '{func_key}' in zone '{zone}'")
                    continue

                if control_rk in command_map:
                    logger.warning(f"[X] DUPLICATE CONTROL ROUTING KEY] {control_rk} already mapped; skipping control under {func_key}")
                    continue

                if callable(func):
                    command_map[control_rk] = func
                    label = control.get("text") or control.get("name") or control.get("type") or "unknown"
                    logger.info(f"[+] MAPPED] {control_rk} -> {func_key}() via '{label}'")
                else:
                    logger.error(f"[X] Could not map '{control_rk}' — no callable found.")

    # 🧠 MANUAL fallback mapping for dropdown-routed variants
    fallback_func = getattr(mod, "load_model", None)

    for zone, funcs in interface_data.items():
        for func_key, entry in funcs.items():
            if func_key == "__static__":
                continue

            base_routing_key = entry.get("routing_key")
            func = getattr(mod, func_key, None)

            if base_routing_key and func_key == "load_model" and callable(func):
                base_root = base_routing_key.rstrip(".0123456789-")
                for base in [".1", ".2"]:
                    for i in range(-1, 26):  # -1 is just .1, rest are .1-a to .1-z
                        suffix = "" if i == -1 else f"-{chr(97 + i)}"
                        rk = f"{base_routing_key}{base}{suffix}"
                        if rk not in command_map:
                            command_map[rk] = func
                            logger.info(f"[+] MAPPED dynamic fallback: {rk} -> {func_key}()")
    return command_map

full_command_map = {}

for filepath, module_name in discovered_modules:
    interface_data = scan_file(filepath, module_name)
    local_map = generate_command_map(interface_data, filepath, module_name)
    full_command_map.update(local_map)

command_map = full_command_map
logger.info(f"COMMAND_MAP_BUILT | size={len(command_map)}")
update_bootstate("router", True)
ROUTER_READY = True

# --- API Route ---
@router.get("/manifest/{module_name}")
def get_module_manifest(module_name: str):
    module_path = os.path.join(MODULE_ROOT, module_name)
    if not os.path.exists(module_path):
        raise HTTPException(status_code=404, detail="Module not found")

    manifest = defaultdict(dict)
    dead_funcs = []

    # Only target functions.py inside the module
    func_file = os.path.join(module_path, "functions.py")
    if not os.path.exists(func_file):
        logger.warning(f"NO_FUNCTIONS_FILE | {module_name} has no functions.py")
        return manifest

    # --- Scan functions.py for UI markers ---
    scan_result = scan_file(func_file, module_name)

    try:
        spec = importlib.util.spec_from_file_location(f"{module_name}.functions", func_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Validate discovered functions exist in module
        for zone, funcs in scan_result.items():
            for fn_name in funcs:
                if fn_name == "__static__":
                    continue
                if not hasattr(module, fn_name):
                    dead_funcs.append(f"{module_name}.{zone}.{fn_name}")

    except Exception as e:
        logger.debug(f"[!] Could not import {func_file}: {e}")

    for zone, content in scan_result.items():
        manifest[zone].update(content)

    if dead_funcs:
        logger.debug(f"[!] Orphaned function declarations: {dead_funcs}")

    # --- Write debug dump (interface_manifest.json) ---
    try:
        debug_output_path = os.path.join(os.path.dirname(__file__), "config", "interface_manifest.json")
        os.makedirs(os.path.dirname(debug_output_path), exist_ok=True)
        with open(debug_output_path, "w") as debug_file:
            json.dump(manifest, debug_file, indent=2)
        terminal_alert(f"[+] DEBUG DUMP: Manifest written to {debug_output_path}", level="INFO")
    except Exception as e:
        terminal_alert(f"[!] Failed to write debug manifest: {e}", level="ERROR")

    return manifest

# --- Endpoint ---
@router.post("/run-command")
async def router_run_command(payload: CommandRequest):
    command = payload.command
    value = payload.value

    logger.info("UI_COMMAND | Received")
    logger.debug(f"ROUTING_KEY | {command}")
    logger.debug(f"PAYLOAD | {json.dumps(value, indent=2)}")
    logger.debug(f"COMMAND_MAP_SIZE | {len(command_map)}")

    if not command or not isinstance(command, str):
        terminal_alert(f"Invalid command: {command}", level="ERROR")
        logger.error(f"INVALID_COMMAND | missing or not a string: {command}")
        return {"status": "bad request", "detail": "Missing or invalid command"}

    logger.debug(f"COMMAND_MAP_FIRST5 | {list(command_map.keys())[:5]}")

    # --- Fallback command handler ---
    def toggle_module(value: dict):
        from api.routes.registery import update_modules, ensure_registry

        module_key = value.get("module")
        enabled = value.get("enabled")

        if module_key is None or enabled is None:
            return {
                "status": "missing module or enabled key",
                "received": value
            }

        registry = ensure_registry()
        if module_key not in registry:
            return {
                "status": "module not found in registry",
                "received": value
            }

        registry[module_key]["enabled"] = enabled
        update_modules(registry)

        return {
            "status": f"module '{module_key}' {'enabled' if enabled else 'disabled'}",
            "updated": registry[module_key]
        }

    # Fallback UI commands
    fallback_map = {
        "set_dropdown": lambda control, selected: {"message": f"Dropdown '{control}' set to '{selected}'"},
        "button_click": lambda control: {"message": f"Button '{control}' clicked"},
        "noop": lambda: {"message": "No operation performed"},
        "toggle_module": toggle_module
    }

    if command in fallback_map:
        try:
            logger.info(f"FALLBACK_HANDLE | {command}")
            result = fallback_map[command](value) if value else fallback_map[command]()
            logger.info(f"FALLBACK_RESULT | {result}")
            return {"status": "executed", "result": result}
        except Exception as e:
            terminal_alert(f"Fallback command '{command}' failed: {e}", level="ERROR")
            logger.error(f"FALLBACK_ERROR | {command} | {e}")
            return {"status": "fallback execution error", "error": str(e), "function": command}

    # Lookup normal command
    func = command_map.get(command)

    if not func:
        similar = [k for k in command_map.keys() if command.split(".")[0] in k]
        logger.debug(f"SUGGESTED_MATCHES | {similar[:5]}")
        terminal_alert(f"UNKNOWN COMMAND — '{command}' not in map", level="WARNING")
        return {
            "status": "unknown command asshole",
            "received": {"command": command, "value": value},
            "suggested_keys": similar[:5]
        }

    if not callable(func):
        terminal_alert(f"Function found but not callable for '{command}'", level="ERROR")
        logger.error(f"NOT_CALLABLE | {command}")
        return {"status": "not callable", "function": command}

    # Auto-bind dropdown to button if missing path, using sibling ".0" control
    if command.endswith(".1") and ("path" not in value or not value.get("path")):
        try:
            sibling_key = command[:-1] + "0"
            sibling_func = command_map.get(sibling_key)
            if sibling_func and callable(sibling_func):
                dropdown_result = sibling_func()
                if isinstance(dropdown_result, dict):
                    for k, arr in dropdown_result.items():
                        if isinstance(arr, list) and arr:
                            value["path"] = arr[0]
                            logger.info(f"AUTO_BIND | Injected path from '{sibling_key}' → {value['path']}")
                            break
                    else:
                        logger.warning(f"AUTO_BIND_EMPTY | No list field in sibling result: {sibling_key}")
                else:
                    logger.warning(f"AUTO_BIND_TYPE | Sibling did not return dict: {sibling_key}")
            else:
                logger.warning(f"AUTO_BIND_NO_SIBLING | No callable for: {sibling_key}")
        except Exception as e:
            logger.warning(f"AUTO_BIND_FAIL | {type(e).__name__} — {e}")

    # Execute main command
    try:
        logger.info(f"EXECUTE | {command}")
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Handle coroutine or normal function
        if asyncio.iscoroutinefunction(func):
            if len(param_names) == 0:
                result = await func()
            elif len(param_names) == 1:
                result = await func(value)
            else:
                result = await func(value, routing_key=command)
        else:
            if len(param_names) == 0:
                result = func()
            elif len(param_names) == 1:
                result = func(value)
            else:
                result = func(value, routing_key=command)

        logger.info(f"RESULT | {result}")
        return {"status": "executed", "result": result}

    except Exception as e:
        tb = traceback.format_exc()
        terminal_alert(f"Execution error for '{command}': {e}", level="ERROR")
        logger.error(f"EXEC_ERROR | {command} | {e}\n{tb}")
        return {"status": "execution error", "error": str(e), "function": command}