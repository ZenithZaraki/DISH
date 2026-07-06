# registery.py
import os
import json
import random
import importlib
from pathlib import Path
from fastapi import APIRouter, HTTPException
from dev.diagnostics import get_logger, terminal_alert

router = APIRouter()
boot_autoregistry_log = []
logger = get_logger("registery")
rterminal_alert = terminal_alert

REGISTRY_READY = False
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
BOOTSTATE_PATH = os.path.join(BASE_DIR, "config", "bootstate.json")
DEFAULT_REGISTRY_PATH = os.path.join(BASE_DIR, "config", "moduleregistry.json")
REGISTRY_FILE = Path(__file__).resolve().parent.parent / "config" / "moduleregistry.json"
USER_REGISTRY_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "userdata", "appconfig", "moduleregistry.json"))
MODULES_DIR = os.path.join(BASE_DIR, "modules")

rterminal_alert("[>] Module Registery initialized...", level="INFO")

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

def scuzify(entry):
    adjectives = [
        "Unstable", "Redundant", "Possessed", "Ghost-Coded", "Overclocked",
        "Cursed", "Deprecated", "Scuzballian", "Mildly Sentient", "Blasphemous",
        "Glitched-Out", "Screaming", "Half-Baked", "Feral", "Twitchy", "Irate",
        "Regret-Inducing", "Disrespectful", "Unholy", "Fucknugget-Class",
        "RAM-Eating", "Hot-Glued", "Unrequested", "Unoptimized", "Accidentally Conscious",
        "Paranoid", "Lobotomized", "Berserk", "Neon-Coated", "Null-Locked",
        "Sadistic", "Spaghetti-Driven", "Ungodly", "Quantum-Tangled", "Overclocked",
        "Patchwork", "Eldritch", "Snark-Infused", "Malware-Bound", "Emotionally Compromised",
        "Cringe-Optimized", "Twitch-Looped", "Duct-Taped", "Rusty", "Hellbound",
        "Unsanctioned", "Overexposed", "Recursive", "Fragmented", "Flammable",
        "Contraband", "Janky", "Malicious", "Bit-Rot Infused"
    ]

    nouns = [
        "Payload", "Snailcore", "Garbage Collector", "Thread Gremlin", "Logic Tumor",
        "Entropy Stack", "Loopstorm", "Possibility Engine", "Failpoint", "Widget of Doubt",
        "Quantum Fuckbox", "Shit Buffer", "Socket Clown", "Nullpointer", "Duck", "Bug Nest",
        "Crash Harness", "Subroutine of Spite", "Compiler Gremlin", "Error Cache",
        "Firmware Curse", "Hellscript", "Bloatwave", "Anxiety Module", "Snarkstack",
        "RAM Coagulator", "Buffer Ferret", "Throttle Goblin", "Segfault Whisperer",
        "Syntax Dumpster", "Invocation Monkey", "Stack Gobbler", "Kernel Nightmare",
        "FPU Screamer", "Loop Decryptor", "Wrench Compiler", "Semicolon Revenant",
        "Packet Stabber", "Socket Parasite", "Quantum Logger", "Latency Leech",
        "OAuth Goblin", "Cryo Cache", "IO Dragon", "Runtime Phantom", "Syscall Kraken",
        "Daemon Clown", "Panic Emitter", "Stack Rotator", "Misalignment Oracle",
        "Shame Archive", "Patch Demon", "Deadlock Puppet", "Loop Squatter"
    ]

    entry_clean = entry.replace("_", " ").title()
    label = f"{random.choice(adjectives)} {random.choice(nouns)}"
    return f"Scuz Unit {label}: {entry_clean}"

def discover_internal_modules():
    internal_modules = []
    for entry in os.listdir(MODULES_DIR):
        mod_path = os.path.join(MODULES_DIR, entry)
        if not os.path.isdir(mod_path):
            continue
        functions_path = os.path.join(mod_path, "functions.py")
        if not os.path.exists(functions_path):
            continue
        try:
            mod = importlib.import_module(f"app.modules.{entry}.functions")
            if hasattr(mod, "router"):
                internal_modules.append((entry, mod.router))
        except Exception as e:
            logger.warning(f"[DISCOVERY] Failed to import module {entry}: {e}")
            continue
    return internal_modules

def mount_internal_modules(app):
    internal_modules = discover_internal_modules()
    for entry, router_obj in internal_modules:
        try:
            mount_path = f"/api/modules/{entry}"
            app.include_router(router_obj, prefix=mount_path, tags=[entry])
            logger.info(f"[INTERNAL MOUNT] Mounted internal module: {entry} at {mount_path}")
        except Exception as e:
            logger.error(f"[INTERNAL MOUNT ERROR] Failed to mount {entry}: {e}")

def ensure_registry():
    logger.info("[REGISTRY] Ensuring registry...")
    modules = {}
    for entry in os.listdir(MODULES_DIR):
        mod_path = os.path.join(MODULES_DIR, entry)
        if os.path.isdir(mod_path) and os.path.exists(os.path.join(mod_path, "functions.py")):
            modules[entry] = {
                "name": entry,
                "display_name": scuzify(entry),
                "enabled": True,
                "locked": False,
                "component": f"/manifest/{entry}"
            }

    def write_registry(path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
            
    # === Handle DEFAULT registry ===
    if not os.path.exists(DEFAULT_REGISTRY_PATH):
        terminal_alert("[BOOT] No default registry found. Creating new registry...", level="WARNING")
        write_registry(DEFAULT_REGISTRY_PATH, modules)
        boot_autoregistry_log.extend(list(modules.keys()))
        return modules
    else:
        try:
            with open(DEFAULT_REGISTRY_PATH, 'r') as f:
                current_registry = json.load(f)
            if not isinstance(current_registry, dict) or not current_registry:
                logger.warning("[REGISTRY] Default registry empty or invalid. Regenerating...")
                write_registry(DEFAULT_REGISTRY_PATH, modules)
                return modules
        except json.JSONDecodeError:
            logger.error("[REGISTRY] Default registry corrupt. Regenerating...")
            write_registry(DEFAULT_REGISTRY_PATH, modules)
            return modules

    # === Merge new modules into DEFAULT registry ===
    updated = False
    for key, val in modules.items():
        if key not in current_registry:
            current_registry[key] = val
            boot_autoregistry_log.append(key)
            updated = True
            terminal_alert(f"[+] Auto-registered new module: {key}", level="INFO")

    if updated:
        write_registry(DEFAULT_REGISTRY_PATH, current_registry)

    # === Handle USER registry ===
    if os.path.exists(USER_REGISTRY_PATH):
        try:
            with open(USER_REGISTRY_PATH, 'r') as f:
                user_registry = json.load(f)
            if not isinstance(user_registry, dict) or not user_registry:
                logger.warning("[REGISTRY] User registry empty/invalid. Falling back to default.")
                return current_registry
            return user_registry
        except json.JSONDecodeError:
            logger.error("[REGISTRY] User registry corrupt. Falling back to default.")
            return current_registry
    else:
        logger.info("[REGISTRY] Using default registry.")
        return current_registry

def mount_active_modules():
    global REGISTRY_READY

    logger.info("[INIT] Mounting active modules...")
    terminal_alert("[>] Mounting active modules...", level="INFO")

    registry = ensure_registry()

    for key, module in registry.items():
        if not module.get("enabled", False):
            continue

        logger.debug(f"[IMPORT] Trying to import: app.modules.{key}.functions")
        try:
            mod = importlib.import_module(f"app.modules.{key}.functions")
            if hasattr(mod, "router"):
                router.include_router(mod.router, prefix=f"/{key}", tags=[module["name"]])
                terminal_alert(f"[+] Mounted module: {key}", level="INFO")
                update_bootstate("module_registry", True)
                logger.info(f"[MOUNT] Mounted module: {key}")
            else:
                terminal_alert(f"[!] Module {key} missing 'router' object", level="WARNING")
                logger.warning(f"[MOUNT] Module {key} missing 'router'")
        except Exception as e:
            terminal_alert(f"[X] Failed to load module '{key}': {e}", level="CRITICAL")
            logger.exception(f"[MOUNT ERROR] Failed to import module {key}: {e}")
            continue
    REGISTERY_READY = True

# -------------------------
# ROUTES
# -------------------------

@router.get("/")
def get_modules():
    try:
        logger.info("[API] GET / — Returning module registry")
        return ensure_registry()
    except Exception as e:
        logger.exception(f"[API ERROR] Failed to get registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load module registry: {str(e)}")

@router.post("/command/toggle_module")
def toggle_module(data: dict):
    try:
        module = data.get("module")
        enabled = data.get("enabled")

        if not module or enabled is None:
            raise HTTPException(status_code=400, detail="Missing module or enabled flag")

        # Load user registry or default
        if os.path.exists(USER_REGISTRY_PATH):
            with open(USER_REGISTRY_PATH, "r") as f:
                registry = json.load(f)
        else:
            registry = ensure_registry()

        if module not in registry:
            raise HTTPException(status_code=404, detail=f"Module '{module}' not found")

        registry[module]["enabled"] = enabled

        # Save update
        os.makedirs(os.path.dirname(USER_REGISTRY_PATH), exist_ok=True)
        with open(USER_REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2)

        logger.info(f"[TOGGLE] Module '{module}' set to enabled={enabled}")
        return {"status": "success", "module": module, "enabled": enabled}

    except Exception as e:
        logger.exception("[ERROR] Failed to toggle module")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
def update_modules(data: dict):
    try:
        logger.info("[API] POST /update — Updating registry")
        os.makedirs(os.path.dirname(USER_REGISTRY_PATH), exist_ok=True)

        # Load current registry
        if os.path.exists(USER_REGISTRY_PATH):
            try:
                with open(USER_REGISTRY_PATH, 'r') as f:
                    current_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("[API] Existing registry corrupt/empty, starting fresh.")
                current_data = {}
        else:
            current_data = {}

        # Merge instead of overwrite
        current_data.update(data)

        # Save merged registry
        with open(USER_REGISTRY_PATH, 'w') as f:
            json.dump(current_data, f, indent=2)

        logger.info("[API] Registry update successful")
        return {"status": "success", "registry": current_data}

    except Exception as e:
        logger.exception(f"[API ERROR] Failed to update registry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update module registry: {str(e)}")

@router.get("/autoregistered")
def get_boot_autoregistry():
    logger.debug("[API] GET /autoregistered")
    return {"autoregistered": boot_autoregistry_log}


