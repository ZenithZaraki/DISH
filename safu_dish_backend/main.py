# main.py
import os
import gc
import sys
import uuid
import json
import time
#import torch
import psutil
import signal
import atexit
import warnings
import traceback
import subprocess
from typing import List
from datetime import datetime
from pydantic import parse_obj_as
from colorama import init, Fore, Style
init()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # safu_dish_backend
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # one level up from safu_dish_backend
APP_PATH = os.path.join(BASE_DIR, "app")

for p in (PROJECT_ROOT, APP_PATH):
    if p not in sys.path:
        sys.path.append(p)

BOOTSTATE_PATH = os.path.join(BASE_DIR, "app", "config", "bootstate.json")
# DISABLE_AUTO_MODEL_LOAD = os.environ.get("DISABLE_AUTO_MODEL_LOAD", "1") == "0"
# if DISABLE_AUTO_MODEL_LOAD:
#     print(Fore.CYAN + "[SECURITY] Auto model loading is DISABLED via DISABLE_AUTO_MODEL_LOAD=1")
# else:
#     print(Fore.YELLOW + "[SECURITY] WARNING: Auto model loading is ENABLED (DISABLE_AUTO_MODEL_LOAD=0)")

DEFAULT_BOOT_STATE = {
    "diagnostics": False,
    "fastapi": False,
    "import_registry": False,
    "module_registry": False,
    "router": False
}

# Suppress specific deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*flash attention.*")

# # ----- GPU PURGE ------ #
# try:
#     if torch.cuda.is_available():
#         torch.cuda.empty_cache()
#         torch.cuda.ipc_collect()
#     gc.collect()
# except Exception as e:
#     print(Fore.YELLOW + f"[!] GPU cleanup failed: {type(e).__name__} — {e}")

def purge_python_subprocesses(targets=("uvicorn", "slloader", "embedder_worker", "torchrun", "scuzlite", "nova_launcher", "fastapi")):
    killed = 0
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if any(t.lower() in cmdline.lower() for t in targets):
                print(Fore.YELLOW + f"[BOOT CLEANUP] Killing leftover: PID={proc.pid} | CMD={cmdline}")
                proc.terminate()
                proc.wait(timeout=3)
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception as e:
            print(Fore.RED + f"[BOOT CLEANUP ERROR] Could not terminate PID {proc.pid}: {e}")
    if killed > 0:
        print(Fore.YELLOW + f"[BOOT CLEANUP] {killed} orphaned subprocess(es) terminated.")
    else:
        print(Fore.LIGHTBLACK_EX + "[BOOT CLEANUP] No orphaned subprocesses found.")

def safe_halt(reason):
    print(Fore.RED + f"[SAFE HALT] {reason}")
    print(Fore.YELLOW + "System halted. Press Ctrl+C to exit manually for debugging.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(Fore.CYAN + "Exiting...")
        sys.exit(0)

def handle_sigterm(*_):
    print(Fore.RED + "[!] SIGTERM received. Cleaning up before exit.")
    shutdown_all()
    safe_halt()


def handle_sigint(*_):
    print(Fore.RED + "[!] SIGINT (Ctrl+C) received. Cleaning up before exit.")
    shutdown_all()
    safe_halt()

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigint)

def initialize_bootstate():
    try:
        if os.path.exists(BOOTSTATE_PATH):
            with open(BOOTSTATE_PATH, "r") as f:
                current = json.load(f)

            if any(current.get(k, False) for k in DEFAULT_BOOT_STATE):
                # Reset all to False
                with open(BOOTSTATE_PATH, "w") as f:
                    json.dump(DEFAULT_BOOT_STATE, f, indent=2)
        else:
            with open(BOOTSTATE_PATH, "w") as f:
                json.dump(DEFAULT_BOOT_STATE, f, indent=2)
    except Exception:
        # On failure, overwrite with safe fallback
        with open(BOOTSTATE_PATH, "w") as f:
            json.dump(DEFAULT_BOOT_STATE, f, indent=2)

def update_bootstate(stage: str, status: bool):
    try:
        with open(BOOTSTATE_PATH, "r") as f:
            state = json.load(f)
        state[stage] = status
        with open(BOOTSTATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(Fore.RED + f"[BOOTSTATE ERROR] Failed to update {stage}: {e}")

initialize_bootstate()

#---BOOT STAGE 1---
import dev.diagnostics as diagnostics

logger = diagnostics.get_logger("main")
wlogger = diagnostics.get_logger("warnings")
terminal_alert = diagnostics.terminal_alert

purge_python_subprocesses()

def boot_diagnostics():
    try:
        diagnostics.initialize_diagnostics()
        if not diagnostics.DIAGNOSTICS_READY:
            raise RuntimeError("Diagnostics failed internal self-check.")
        terminal_alert("[+] Diagnostics system online.", level="INFO")
        update_bootstate("diagnostics", True)
        return True
    except Exception as e:
        print(Fore.RED + "[BOOT ERROR] Diagnostics failed to initialize:")
        print(f"  Reason: {type(e).__name__} - {e}")
        return False

# --- DIAGNOSTICS SYSTEM INIT ---
logger.info("MAIN_LAUNCH | Testing logger from main.py")
terminal_alert("[>] Boot initialized...", level="BOOTING")

if not boot_diagnostics():
    print(Fore.RED + "[SYSTEM HALT] Diagnostics boot failed. Aborting boot sequence.")
    safe_halt("Stage boot_diagnostics failed")


from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ---BOOT STAGE 2---
def boot_fastapi():
    terminal_alert("[>] Fast API initialized...", level="INFO")
    global app
    try:
        app = FastAPI()
        
        # CORS CONFIG
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Sanity check: confirm basic route registration is working
        @app.get("/__bootcheck__")
        def boot_check():
            return {"status": "ok"}

        # Simulate internal call to that route (test the app)
        from fastapi.testclient import TestClient
        test_client = TestClient(app)
        response = test_client.get("/__bootcheck__")

        if response.status_code != 200 or response.json().get("status") != "ok":
            raise RuntimeError("FastAPI internal test route failed.")

        terminal_alert("[+] FastAPI core initialized.", level="INFO")
        update_bootstate("fastapi", True)
        return True

    except Exception as e:
        logger.exception(f"[BOOT ERROR] FastAPI failed to initialize | {type(e).__name__}: {e}")
        terminal_alert("[BOOT ERROR] FastAPI failed to initialize", level="CRITICAL")
        terminal_alert(f"  Reason: {type(e).__name__} — {e}", level="CRITICAL")
        return False

if not boot_fastapi():
    terminal_alert("[SYSTEM HALT] FastAPI core boot failed. Aborting boot sequence.", level="CRITICAL")
    safe_halt("Stage Fast API failed")

# COMMAND ROUTES
@app.post("/run-command")
async def run_command(payload: dict):
    logger.warning("[+] Proxying /run-command to router.py handler...")

    try:
        translated_payload = parse_obj_as(CommandRequest, payload)
    except Exception as e:
        logger.error(f"[X] Failed to parse payload into CommandRequest: {e}")
        return {
            "status": "invalid payload",
            "error": str(e),
            "expected_format": {"command": "str", "value": "dict"}
        }

    return await router_run_command(translated_payload)

# FILE UPLOAD
@app.post("/uploads")
async def upload_files(files: List[UploadFile] = File(...)):
    uploaded = []
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    for file in files:
        content = await file.read()
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(content)
        uploaded.append(file.filename)
        logger.info(f" Uploaded: {file.filename} ({len(content)} bytes)")
    
    return {"status": "success", "files": uploaded}

# ROOT
@app.get("/")
def read_root():
    return {"message": "SAFU DISH Online"}

# ERROR HANDLERS
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = f"ERR-{uuid.uuid4().hex[:8]}"
    logger.error(f"[{error_id}] Unhandled exception at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "Something went wrong on the server.",
            "error_id": error_id
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.detail} at {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Request Failed", "detail": exc.detail},
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    error_id = f"VAL-{uuid.uuid4().hex[:8]}"
    logger.warning(f"[{error_id}] ValueError: {exc} at {request.url}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "detail": str(exc),
            "error_id": error_id
        },
    )

# ---BOOT STAGE 4----
def boot_module_registery(max_wait_time=10, retry_interval=1.5):
    try:
        from app.api.routes import registery

        # --- Mount active modules from registry ---
        registery.mount_active_modules()

        # --- Wait until bootstate.json reports module_registry = true ---
        waited = 0
        while True:
            if waited >= max_wait_time:
                raise TimeoutError("Module Registry did not report ready state after timeout.")

            try:
                with open(BOOTSTATE_PATH, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("module_registry", False):
                    break
            except Exception:
                pass  # Silently retry

            terminal_alert("Waiting on Module Registry to become ready (bootstate.json)...", level="DEBUG")
            time.sleep(retry_interval)
            waited += retry_interval

        # --- Auto-discover and mount internal routers ---
        registery.mount_internal_modules(app)

        # --- Mount internal router to expose registry and endpoints ---
        from app.api.routes.registery import router as internal_module_router
        app.include_router(registery.router, prefix="/api/modules", tags=["registry"])
        app.include_router(internal_module_router, prefix="/api/modules")
        app.include_router(internal_module_router, prefix="/api")

        terminal_alert("[+] Module Registry online.", level="INFO")
        return True

    except Exception as e:
        logger.exception(f"[BOOT ERROR] Module Registry failed to initialize | {type(e).__name__}: {e}")
        terminal_alert("[BOOT ERROR] Module Registry failed to initialize", level="CRITICAL")
        terminal_alert(f"  Reason: {type(e).__name__} — {e}", level="CRITICAL")
        return False

# --- MODULE REGISTRY INIT ---
if not boot_module_registery():
    terminal_alert("[SYSTEM HALT] Module Registry boot failed. Aborting boot sequence.", level="CRITICAL")
    safe_halt("Stage module registery failed")

# --- ROUTE: Module Registry Viewer ---
REGISTRY_PATH = os.path.join("app", "config", "moduleregistry.json")

@app.get("/api/modules/registry")
def get_module_registry():
    try:
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[ERROR] Could not read module registry: {e}")
        raise HTTPException(status_code=500, detail="Failed to load module registry.")

# ---BOOT STAGE 5---
def boot_dish_router(max_wait_time=10, retry_interval=0.5):
    try:
        BOOTSTATE_PATH = os.path.join(BASE_DIR, "app", "config", "bootstate.json")

        # --- Wait until bootstate.json reports module_registry = true ---
        waited = 0
        while True:
            if waited >= max_wait_time:
                raise TimeoutError("Module Registry not ready after timeout.")

            try:
                with open(BOOTSTATE_PATH, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("module_registry", False):
                    break
            except Exception:
                pass  # Silent retry

            terminal_alert("Waiting on Module Registry to become ready before loading Router (bootstate.json)...", level="DEBUG")
            time.sleep(retry_interval)
            waited += retry_interval

        from app import router

        if not getattr(router, "ROUTER_READY", False):
            raise RuntimeError("DISH Router did not report ready state.")

        from app.router import router as manifest_router
        from app.router import router_run_command, CommandRequest

        global router_run_command, CommandRequest
        router_run_command = router_run_command
        CommandRequest = CommandRequest

        app.include_router(manifest_router, prefix="/api")
        terminal_alert("[+] DISH Router online.", level="INFO")
        return True

    except Exception as e:
        logger.exception(f"[BOOT ERROR] DISH Router failed to initialize | {type(e).__name__}: {e}")
        terminal_alert("[BOOT ERROR] DISH Router failed to initialize", level="CRITICAL")
        terminal_alert(f"  Reason: {type(e).__name__} — {e}", level="CRITICAL")
        return False

# --- DISH ROUTER INIT ---
if not boot_dish_router():
    terminal_alert("[SYSTEM HALT] DISH Command Router boot failed. Aborting boot sequence.", level="CRITICAL")
    safe_halt("Stage DISH router failed")

@app.get("/__routes__")
def list_routes():
    return [r.path for r in app.routes]

def warning_to_logger(message, category, filename, lineno, file=None, line=None):
    wlogger.warning(f"{category.__name__}: {message} | {filename}:{lineno}")

def shutdown_all():
     try:
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
     except Exception:
         pass
    #  vector_embedder.stop_scuzlite()
    #  vector_embedder.stop_embedder()
     purge_python_subprocesses()
     # Any other cleanup...

atexit.register(shutdown_all)

warnings.showwarning = warning_to_logger

terminal_alert(f"[>] MAIN.PY using Python from: {sys.executable}", level="INFO")
terminal_alert("WELCOME TO:", level="ACTIVATED")
logger.info("[+] MAIN.PY LOADED")
print(Fore.LIGHTBLACK_EX + "\n" + "=" * 32)
print("SKYTEAM AEROSPACE FOUNDATION")
print("D.I.S.H. CORE — Digital Intelligence Stack Host")
print("Version 1.3 | Modular APM Architecture Initialized")
print(f"{Fore.YELLOW}Caution:{Style.RESET_ALL} Core functions operating in standalone mode.")
print(Fore.LIGHTBLACK_EX + "=" * 32)
print(Fore.LIGHTGREEN_EX + "           ONLINE")
print(Fore.LIGHTBLACK_EX + "=" * 32 + "\n" + Style.RESET_ALL)
