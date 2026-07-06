# Test APM functions.py
# FastAPI wrapper for basic model load, generate, and stop
import os
import re
import sys
import wmi
import time
import json
import ctypes
import aiohttp
import asyncio
import threading
import traceback
import websockets
import subprocess
import nest_asyncio
from pathlib import Path
from threading import Lock
from ctypes import wintypes
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Query, HTTPException

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from dev.diagnostics import get_logger, terminal_alert

# -------------------- Init -------------------- #
runtime = None
router = APIRouter()
runtime_lock = Lock()
dterminal = terminal_alert
restart_after_generation = False
generation_active = False
restart_after_generation = False
last_generation_end = 0
last_generation_activity = 0
_watchdog_started = False
_last_model_use = datetime.utcnow()
dlogger = get_logger("Test_APM.functions")

def reset_idle_timer():
    global _last_model_use
    _last_model_use = datetime.utcnow()
    dlogger.debug(f"[IDLE_TIMER] Reset at {_last_model_use.isoformat()}")
    dterminal(f"[IDLE_TIMER] Reset at {_last_model_use.isoformat()}", level="INFO")

EMBEDDER_API = "http://127.0.0.1:8007"
EMBEDDER_PROC = None
PROC_PID = None
PROC = None 

PDH_FMT_DOUBLE = 0x00000200

_pdh = ctypes.windll.pdh
_gpu_query = None
_gpu_counter = None

# ----------------- Utility Functions ----------------- #
# Global runtime memory estimate (updated by telemetry)
runtime_vram_usage_mb = 0

def update_runtime_vram_usage(mb):
    global runtime_vram_usage_mb
    runtime_vram_usage_mb = mb

# -----------------------------------------------------
# GPU TOTAL VRAM DETECTION
# -----------------------------------------------------
def get_gpu_vram_totals():
    import wmi

    gpus = []
    w = wmi.WMI(namespace="root\\CIMV2")

    for gpu in w.Win32_VideoController():
        name = gpu.Name

        try:
            total_mb = int(gpu.AdapterRAM) // (1024**2)
        except:
            total_mb = 0

        # Fallbacks if Windows fails to report VRAM
        if total_mb <= 0:
            if "7900" in name:
                total_mb = 24576
            elif "4080" in name:
                total_mb = 16384
            else:
                total_mb = 8192

        gpus.append((name, total_mb))

    return gpus

def init_gpu_vram_counter():
    """
    Initialize Windows GPU VRAM performance counter.
    """
    global _gpu_query, _gpu_counter

    try:
        _gpu_query = wintypes.HANDLE()
        _gpu_counter = wintypes.HANDLE()

        _pdh.PdhOpenQueryW(None, None, ctypes.byref(_gpu_query))

        _pdh.PdhAddEnglishCounterW(
            _gpu_query,
            "\\GPU Adapter Memory(*)\\Dedicated Usage",
            None,
            ctypes.byref(_gpu_counter)
        )

        _pdh.PdhCollectQueryData(_gpu_query)

        dterminal("[VRAM] GPU telemetry initialized.", level="INFO")

    except Exception as e:
        dlogger.warning(f"[VRAM_INIT_FAIL] {e}")

# -----------------------------------------------------
# REAL GPU VRAM USAGE (WINDOWS PERFORMANCE COUNTERS)
# -----------------------------------------------------
def get_gpu_vram_usage_mb():

    global _gpu_query, _gpu_counter

    try:
        if _gpu_query is None:
            return 0

        _pdh.PdhCollectQueryData(_gpu_query)

        class PDH_FMT_COUNTERVALUE(ctypes.Structure):
            _fields_ = [
                ("CStatus", wintypes.DWORD),
                ("doubleValue", ctypes.c_double),
            ]

        value = PDH_FMT_COUNTERVALUE()

        _pdh.PdhGetFormattedCounterValue(
            _gpu_counter,
            PDH_FMT_DOUBLE,
            None,
            ctypes.byref(value)
        )

        bytes_used = value.doubleValue
        mb_used = bytes_used / (1024 * 1024)

        return int(mb_used)

    except Exception as e:
        dlogger.warning(f"[VRAM_MONITOR_FAIL] {e}")
        return 0

# -----------------------------------------------------
# TELEMETRY THREAD (CONTINUOUS VRAM MONITORING)
# -----------------------------------------------------
def start_vram_telemetry(interval=1.0):
    """
    Continuously updates runtime_vram_usage_mb from GPU telemetry.
    """

    def loop():
        while True:
            try:
                usage = get_gpu_vram_usage_mb()
                update_runtime_vram_usage(usage)
            except Exception as e:
                dlogger.warning(f"[VRAM_TELEMETRY_FAIL] {e}")

            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()


# -----------------------------------------------------
# VRAM WATCHDOG
# -----------------------------------------------------
def vram_watchdog(
    gpu_total_mb,
    soft_range=(75, 86),
    hard_range=(87, 96),
    check_interval=2,
    cooldown_seconds=6,
    activity_grace_seconds=5,
    auto_restart=True
):

    global _watchdog_started

    # Prevent multiple watchdog threads
    if _watchdog_started:
        return
    _watchdog_started = True

    def monitor():

        global restart_after_generation
        global generation_active
        global last_generation_end
        global last_generation_activity

        warned = False

        while True:

            # Runtime not running
            if PROC is None or PROC.poll() is not None:
                time.sleep(check_interval)
                continue

            usage_mb = runtime_vram_usage_mb
            usage_pct = (usage_mb / gpu_total_mb) * 100 if gpu_total_mb else 0

            # Guard against telemetry glitches
            if usage_mb > gpu_total_mb * 4:
                dlogger.warning(
                    f"[WATCHDOG] Ignoring impossible VRAM reading: {usage_mb}MB"
                )
                time.sleep(check_interval)
                continue

            dlogger.debug(
                f"[VRAM] {usage_mb}MB / {gpu_total_mb}MB ({usage_pct:.2f}%)"
            )

            now = time.time()

            # Treat generation as active if tokens seen recently
            generation_recent = (
                generation_active or
                (now - last_generation_activity) < activity_grace_seconds
            )

            # ------------------------------------------------
            # Handle scheduled restart AFTER generation ends
            # ------------------------------------------------
            if restart_after_generation:

                if not generation_recent:

                    idle_time = now - last_generation_end

                    if idle_time >= cooldown_seconds:

                        dterminal(
                            "[WATCHDOG] Executing scheduled restart.",
                            level="WARNING"
                        )

                        stop_dml_runtime()

                        if auto_restart:
                            time.sleep(1)
                            start_dml_runtime()

                        restart_after_generation = False
                        warned = False

                time.sleep(check_interval)
                continue

            # ------------------------------------------------
            # Soft threshold band
            # ------------------------------------------------
            if soft_range[0] <= usage_pct <= soft_range[1] and not warned:

                dterminal(
                    f"[WATCHDOG] VRAM high ({usage_pct:.1f}%)",
                    level="WARNING"
                )

                warned = True

            # ------------------------------------------------
            # Hard threshold band
            # ------------------------------------------------
            if usage_pct >= hard_range[0] and not restart_after_generation:

                if generation_recent:

                    dterminal(
                        f"[WATCHDOG] VRAM critical ({usage_pct:.1f}%) — restart scheduled after generation.",
                        level="ERROR"
                    )

                    restart_after_generation = True

                else:

                    idle_time = now - last_generation_end

                    # Wait for VRAM cleanup cooldown
                    if idle_time < cooldown_seconds:

                        dlogger.debug(
                            f"[WATCHDOG] VRAM high but waiting for cooldown ({idle_time:.1f}s)"
                        )

                    else:

                        dterminal(
                            f"[WATCHDOG] VRAM critical ({usage_pct:.1f}%) — restarting runtime immediately.",
                            level="ERROR"
                        )

                        stop_dml_runtime()

                        if auto_restart:
                            time.sleep(1)
                            start_dml_runtime()

                warned = False

            # ------------------------------------------------
            # Reset warning when memory recovers
            # ------------------------------------------------
            if usage_pct < soft_range[0]:
                warned = False

            time.sleep(check_interval)

    threading.Thread(target=monitor, daemon=True).start()

# -----------------------------------------------------
# START TELEMETRY IMMEDIATELY
# -----------------------------------------------------
init_gpu_vram_counter()
start_vram_telemetry(interval=1.0)

def start_dml_runtime(manual: bool = True):
    """
    Starts the DirectML subprocess, ensures it's tracked,
    streams logs live, and verifies the WebSocket runtime comes online.
    """
    global PROC, PROC_PID

    with runtime_lock:
        pid_file = Path(__file__).parent / "runtime_pid.txt"
        runtime_path = Path(__file__).parent / "test_inference.py"

        # ───────────── Stale PID Cleanup ─────────────
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text().strip())
                import psutil
                if not psutil.pid_exists(old_pid):
                    pid_file.unlink()
                    dterminal(f"[DISH] Stale PID {old_pid} cleaned up.", level="WARN")
            except Exception as e:
                dterminal(f"[DISH] Failed to clean up old PID: {e}", level="WARN")
                try:
                    pid_file.unlink()
                except:
                    pass

        # ───────────── Check for Active Subprocess ─────────────
        if PROC and hasattr(PROC, "poll") and PROC.poll() is None:
            dterminal("[DISH] Runtime already active.", level="WARN")
            return PROC

        # ───────────── Validate Runtime Path ─────────────
        if not runtime_path.exists():
            raise FileNotFoundError(f"Runtime script not found: {runtime_path}")

        # ───────────── Launch Subprocess ─────────────
        python_exec = sys.executable
        dterminal(f"[DISH] Using Python executable: {python_exec}", level="INFO")

        try:
            PROC = subprocess.Popen(
                [python_exec, "-u", str(runtime_path)],
                cwd=Path(__file__).parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # line‑buffered for live streaming
            )
            PROC_PID = PROC.pid
            pid_file.write_text(str(PROC_PID))
            dterminal(f"[DISH] DirectML subprocess started (PID: {PROC_PID})", level="INFO")
            # ───────────── Launch VRAM Watchdog ─────────────
            try:
                gpus = get_gpu_vram_totals()

                if not gpus:
                    dterminal("[WATCHDOG] No GPUs detected.", level="ERROR")
                else:

                    # Prefer AMD if DirectML runtime
                    gpu_name = None
                    gpu_total_mb = None

                    for name, total in gpus:
                        if "AMD" in name or "Radeon" in name:
                            gpu_name = name
                            gpu_total_mb = total
                            break

                    # fallback if AMD not found
                    if gpu_total_mb is None:
                        gpu_name, gpu_total_mb = gpus[0]

                    dterminal(
                        f"[WATCHDOG] Monitoring VRAM on {gpu_name} ({gpu_total_mb}MB)",
                        level="INFO"
                    )

                    vram_watchdog(gpu_total_mb)

                    dterminal("[DISH] VRAM watchdog activated.", level="INFO")

            except Exception as e:
                dterminal(f"[WATCHDOG] Failed to start: {e}", level="WARN")
        except Exception as e:
            raise RuntimeError(f"[FATAL] Failed to launch DirectML runtime: {e}")

        # ────────────────────────────────────────────────
        # Stream subprocess logs live
        # ────────────────────────────────────────────────
        def _pipe_reader(stream, level):
            error_keywords = re.compile(r"(error|failed|exception|traceback)", re.IGNORECASE)
            try:
                for line in iter(stream.readline, ''):
                    if line.strip():
                        tag = "ERROR" if error_keywords.search(line) else level
                        dterminal(f"[SUBPROC] {line.strip()}", level=tag)
                stream.close()
            except Exception as e:
                dterminal(f"[PIPE_READER_FAIL] {e}", level="WARN")

        threading.Thread(target=_pipe_reader, args=(PROC.stdout, "INFO"), daemon=True).start()
        threading.Thread(target=_pipe_reader, args=(PROC.stderr, "ERROR"), daemon=True).start()

        # ────────────────────────────────────────────────
        # Verify WebSocket comes online
        # ────────────────────────────────────────────────
        async def _verify_ws(uri: str, retries: int = 60, delay: float = 3.0):
            for attempt in range(retries):
                if PROC.poll() is not None:
                    raise RuntimeError("DirectML subprocess exited before WebSocket ready.")
                try:
                    async with websockets.connect(uri) as ws:
                        await ws.send(json.dumps({"ping": True}))
                        await ws.close()
                        return True
                except Exception:
                    await asyncio.sleep(delay)
            return False

        uri = "ws://127.0.0.1:8765"
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                nest_asyncio.apply()
                success = loop.run_until_complete(_verify_ws(uri))
            else:
                success = asyncio.run(_verify_ws(uri))
        except RuntimeError:
            success = asyncio.run(_verify_ws(uri))

        if not success:
            dterminal("[ERROR] DirectML WebSocket runtime failed to respond.", level="ERROR")
            PROC.kill()
            raise RuntimeError("WebSocket runtime failed to respond after subprocess launch.")

        return PROC

def stop_dml_runtime():
    """
    Safely terminates the DirectML subprocess and cleans up resources.
    Thread-safe and race-protected to prevent concurrent modification.
    """
    global PROC, _auto_restart_block
    _auto_restart_block = True
    pid_file = Path(__file__).parent / "runtime_pid.txt"

    with runtime_lock:
        # ────────────────────────────────────────────────
        # Check if a valid process exists
        # ────────────────────────────────────────────────
        if not PROC or not callable(getattr(PROC, "poll", None)):
            dterminal("[DISH] No valid subprocess handle to terminate.", level="WARN")
            PROC = None

            # Clean up any stale PID file
            if pid_file.exists():
                try:
                    pid_file.unlink()
                    dterminal("[DISH] Stale PID file removed.", level="INFO")
                except Exception as e:
                    dterminal(f"[WARN] Failed to remove stale PID file: {e}", level="WARN")
            return

        # ────────────────────────────────────────────────
        # Attempt to send a stop signal via WebSocket first
        # ────────────────────────────────────────────────
        if PROC and hasattr(PROC, "poll") and PROC.poll() is None:
            try:
                uri = "ws://127.0.0.1:8765"

                async def send_stop_signal():
                    try:
                        async with websockets.connect(uri) as ws:
                            await ws.send(json.dumps({"cmd": "stop"}))
                            await ws.close()
                            dterminal("[DISH] Stop signal sent over WebSocket.", level="INFO")
                    except Exception as e:
                        dterminal(f"[WARN] WebSocket stop signal failed: {e}", level="WARN")

                # Run async safely in current loop context
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        nest_asyncio.apply()
                        loop.run_until_complete(send_stop_signal())
                    else:
                        asyncio.run(send_stop_signal())
                except Exception as e:
                    dterminal(f"[WARN] WebSocket pre-stop phase failed: {e}", level="WARN")

            except Exception as e:
                dterminal(f"[WARN] WebSocket connection attempt failed: {e}", level="WARN")

        # ────────────────────────────────────────────────
        # Attempt graceful shutdown
        # ────────────────────────────────────────────────
        try:
            if PROC and hasattr(PROC, "pid"):
                dterminal(f"[DISH] Attempting to terminate DirectML subprocess (PID: {PROC.pid})", level="INFO")
                PROC.terminate()
                try:
                    PROC.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    dterminal("[DISH] Graceful termination timed out. Forcing kill...", level="WARN")
                    PROC.kill()
                    PROC.wait(timeout=2)
            else:
                dterminal("[DISH] No valid PID found for subprocess.", level="WARN")
        except Exception as e:
            dterminal(f"[ERROR] Failed to terminate subprocess: {e}", level="ERROR")
        finally:
            try:
                PROC = None
                if pid_file.exists():
                    try:
                        pid_file.unlink()
                        dterminal("[DISH] PID file removed.", level="INFO")
                    except Exception as e:
                        dterminal(f"[WARN] Failed to remove PID file: {e}", level="WARN")
            except Exception as e:
                dterminal(f"[WARN] Cleanup phase encountered an error: {e}", level="WARN")

            dterminal("[DISH] DirectML subprocess fully shut down.", level="SUCCESS")
            time.sleep(2)
            _auto_restart_block = False

# ----------------- Embedder Runtime Management ----------------- #
def start_embedder_runtime():
    """Launches embedder_worker.py as a FastAPI subprocess and verifies its /ping endpoint."""
    global EMBEDDER_PROC
    pid_file = Path(__file__).parent / "embedder_pid.txt"
    embedder_path = Path(__file__).parent / "embedder_worker.py"

    if not embedder_path.exists():
        raise FileNotFoundError(f"Embedder script not found: {embedder_path}")

    if EMBEDDER_PROC and EMBEDDER_PROC.poll() is None:
        dterminal("[EMBEDDER] Already running.", level="WARN")
        return EMBEDDER_PROC

    python_exec = sys.executable
    dterminal(f"[EMBEDDER] Launching FastAPI embedder_worker.py using {python_exec}", level="INFO")

    try:
        EMBEDDER_PROC = subprocess.Popen(
            [python_exec, "-u", str(embedder_path)],
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        pid_file.write_text(str(EMBEDDER_PROC.pid))
        dterminal(f"[EMBEDDER] Started (PID: {EMBEDDER_PROC.pid})", level="SUCCESS")
    except Exception as e:
        raise RuntimeError(f"[EMBEDDER_FAIL] Failed to launch: {e}")

    # Stream its logs
    def _pipe_reader(stream, tag):
        for line in iter(stream.readline, ''):
            if line.strip():
                dterminal(f"[EMBEDDER:{tag}] {line.strip()}", level=tag)
        stream.close()

    threading.Thread(target=_pipe_reader, args=(EMBEDDER_PROC.stdout, "INFO"), daemon=True).start()
    threading.Thread(target=_pipe_reader, args=(EMBEDDER_PROC.stderr, "ERROR"), daemon=True).start()

    # Verify HTTP endpoint comes online
    async def _verify_http(retries=25, delay=1.0):
        url = "http://127.0.0.1:8007/ping"
        for _ in range(retries):
            if EMBEDDER_PROC.poll() is not None:
                return False
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            return True
            except Exception:
                await asyncio.sleep(delay)
        return False

    try:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(_verify_http())
    except RuntimeError:
        success = asyncio.run(_verify_http())

    if not success:
        dterminal("[EMBEDDER] /ping verification failed.", level="ERROR")
        EMBEDDER_PROC.kill()
        raise RuntimeError("Embedder service did not come online in time.")

    dterminal("[EMBEDDER] Verified /ping endpoint online.", level="SUCCESS")
    return EMBEDDER_PROC

def stop_embedder_runtime():
    """Stops the embedder FastAPI subprocess."""
    global EMBEDDER_PROC
    pid_file = Path(__file__).parent / "embedder_pid.txt"

    if not EMBEDDER_PROC or EMBEDDER_PROC.poll() is not None:
        dterminal("[EMBEDDER] No active embedder process found.", level="WARN")
        if pid_file.exists():
            pid_file.unlink()
        return

    try:
        dterminal(f"[EMBEDDER] Terminating PID {EMBEDDER_PROC.pid}...", level="INFO")
        EMBEDDER_PROC.terminate()
        EMBEDDER_PROC.wait(timeout=3)
    except subprocess.TimeoutExpired:
        EMBEDDER_PROC.kill()
        EMBEDDER_PROC.wait(timeout=2)
    except Exception as e:
        dterminal(f"[EMBEDDER_STOP_FAIL] {e}", level="ERROR")
    finally:
        EMBEDDER_PROC = None
        if pid_file.exists():
            pid_file.unlink()
        dterminal("[EMBEDDER] Stopped successfully.", level="SUCCESS")

async def runtime_is_alive(uri: str = "ws://127.0.0.1:8765") -> bool:
    """Check if the DirectML WebSocket runtime is responsive."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(uri, timeout=2) as ws:
                await ws.send_json({"ping": True})
                return True
    except:
        return False

async def stream_from_runtime(prompt):
    """
    Opens a WebSocket connection to the DirectML runtime and yields tokens in streaming mode.
    """
    if not prompt:
        yield "[Error] No prompt provided to streaming engine."
        return

    uri = "ws://127.0.0.1:8765"

    if not await runtime_is_alive(uri) and not _auto_restart_block:
        dterminal("[AUTO-RESTART] Runtime inactive. Relaunching DML subprocess...", level="INFO")
        start_dml_runtime()

    for attempt in range(5):
        try:
            dlogger.info(f"[STREAM] Attempt {attempt+1} — Connecting to WebSocket runtime...")
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"prompt": prompt, "stream": True}))

                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        if "token" in data:
                            yield data["token"]
                        elif data.get("done"):
                            dlogger.info("[STREAM] Inference complete.")
                            return
                    except Exception as e:
                        dlogger.warning(f"[STREAM_PARSE_FAIL] Invalid JSON: {e}")
                        yield f"[Error] Token parse error: {e}"

            break  # Exit loop after successful run

        except (ConnectionRefusedError, OSError) as e:
            await asyncio.sleep(0.5)
            dlogger.warning(f"[STREAM_RETRY] Connection failed: {e}")
            continue

        except Exception as e:
            dlogger.error(f"[STREAM_FAIL] {type(e).__name__}: {e}")
            yield f"[WebSocket Error] {e}"
            return

    yield "[Error] DirectML runtime unreachable after retries."

# -------------------- UI Bindings -------------------- #
# @ui_group "DISH Test APM"
# @ui_zone "sidebar"
# @ui_key DISH.sidebar.start_runtime_api
# @ui button text="Load Model"

@router.post("/dish/load")
def start_runtime_api(manual: bool = Query(True)):
    """
    Launches both the DirectML inference runtime and the FastAPI embedder service.
    """
    try:
        # --- Start DirectML runtime ---
        proc = start_dml_runtime(manual=manual)
        if not proc or proc.poll() is not None:
            raise RuntimeError("DirectML runtime failed to start.")

        # # --- Start embedder FastAPI runtime ---
        # embedder_proc = start_embedder_runtime()
        # if not embedder_proc or embedder_proc.poll() is not None:
        #     raise RuntimeError("Embedder service failed to start.")

        msg = (
            f"Both runtimes active — DirectML PID: {proc.pid}, "
            #f"Embedder PID: {embedder_proc.pid}"
        )
        dlogger.info(f"[DISH] {msg}")
        dterminal(f"[DISH] {msg}", level="SUCCESS")
        return {"status": msg}

    except Exception as e:
        tb = traceback.format_exc()
        dlogger.error(f"[LOAD_FAIL] {type(e).__name__}: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Launch failed: {e}")
    
# @ui_group "DISH Test APM"
# @ui_zone "sidebar"
# @ui_key DISH.sidebar.stop_generation_api
# @ui button text="Stop Generation"

@router.post("/dish/stop")
async def stop_generation_api():
    """
    Sends a stop command to the DirectML runtime (if active),
    via WebSocket. Returns a status message.
    """
    uri = "ws://127.0.0.1:8765"

    # ────────────────────────────────────────────────
    # Attempt WebSocket Stop Signal
    # ────────────────────────────────────────────────
    try:
        async with websockets.connect(uri, open_timeout=2, close_timeout=1) as ws:
            await ws.send(json.dumps({"cmd": "stop"}))

        msg = f"Stop signal sent to DirectML subprocess (PID: {PROC.pid})"
        dlogger.info(f"[DISH] {msg}")
        dterminal(f"[DISH] {msg}", level="INFO")
        return {"status": msg}

    except (ConnectionRefusedError, websockets.exceptions.InvalidURI) as e:
        msg = "WebSocket connection failed — process may not be ready or already stopped."
        dlogger.warning(f"[DISH] {msg}")
        dterminal(f"[DISH] {msg}", level="WARN")
        return {"status": msg}

    except Exception as e:
        tb = traceback.format_exc()
        dlogger.error(f"[STOP_WS_FAIL] {type(e).__name__}: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"Failed to stop subprocess via WebSocket: {e}")
    
# @ui_group "DISH Test APM"
# @ui_zone "sidebar"
# @ui_key DISH.sidebar.stop_runtime_api
# @ui button text="Unload Model"

@router.post("/dish/unload")
def unload_runtime_api():
    """
    Stops both the DirectML inference runtime and the embedder FastAPI subprocess.
    """
    try:
        stop_embedder_runtime()
        stop_dml_runtime()

        msg = "Both DirectML and Embedder services stopped."
        dlogger.info(f"[DISH] {msg}")
        dterminal(f"[DISH] {msg}", level="SUCCESS")
        return {"status": msg}
    except Exception as e:
        tb = traceback.format_exc()
        dlogger.error(f"[STOP_FAIL] {type(e).__name__}: {e}\n{tb}")
        dterminal(f"[ERROR] Failed to stop runtimes: {e}", level="ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to stop runtimes: {e}")

# -------------------- Chatbox -------------------- #
# @ui_group "DISH Chat Portal"
# @ui_zone "main"
# @ui_key main.dish.chatbox.01
# @ui chatbox

class PromptRequest(BaseModel):
    message: str
    instruction: Optional[str] = ""
    history: Optional[list] = []
    session_id: Optional[str] = "default-session"
    use_context: Optional[bool] = True

@router.post("/dish/respond")
async def dish_generate_reply(
    request: PromptRequest,
    stream: bool = Query(False)
):
    """
    Routes prompt requests to the DirectML WebSocket runtime.
    Integrates with the FastAPI embedder service for memory context and chat saving.
    """
    import json, asyncio, websockets, aiohttp, uuid

    EMBEDDER_API = "http://127.0.0.1:8007"
    session_id = request.session_id or "default-session"  # replace later with real user session management

    instruction = request.instruction.strip() if request.instruction else ""
    prompt = request.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is empty.")
    
    global generation_active, last_generation_activity

    generation_active = True
    last_generation_activity = time.time()

    uri = "ws://127.0.0.1:8765"

    async def runtime_is_alive() -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(uri, timeout=2) as ws:
                    await ws.send_json({"ping": True})
                    return True
        except Exception:
            return False

    if not await runtime_is_alive():
        dterminal("[AUTO-RESTART] Runtime inactive. Relaunching DML subprocess...", level="INFO")
        start_dml_runtime()

    dlogger.info(f"[DISH_INPUT] {instruction}, {prompt}")

    # ────────────────────────────────────────────────
    # STEP 0 — Build Rolling Context Window
    # ────────────────────────────────────────────────

    history_text = ""

    if request.use_context and request.history:

        # VRAM-safe message limit
        MAX_HISTORY_MESSAGES = 10

        recent_history = request.history[-MAX_HISTORY_MESSAGES:]

        cleaned = []

        for msg in recent_history:

            role = msg.get("role", "user")
            content = msg.get("content", "").strip()

            if not content:
                continue

            # remove UI placeholders
            if content.startswith("__"):
                continue

            role_label = "User" if role == "user" else "Assistant"
            cleaned.append(f"{role_label}: {content}")

        history_text = "\n".join(cleaned)

    # ────────────────────────────────────────────────
    # STEP 1 — Retrieve Semantic Context
    # ────────────────────────────────────────────────
    async def get_chat_context():

        try:

            async with aiohttp.ClientSession() as session:

                payload = {
                    "session_id": session_id,
                    "query": prompt,
                    "k": 6,
                    "include_metadata": True
                }

                dlogger.info(
                    f"[CTX_FETCH] session={session_id} query='{prompt}'"
                )

                async with session.post(
                    f"{EMBEDDER_API}/chat/context",
                    json=payload
                ) as resp:

                    if resp.status != 200:
                        dlogger.warning(
                            f"[CTX_FETCH_FAIL] embedder returned {resp.status}"
                        )
                        return ""

                    data = await resp.json()
                    context_items = data.get("context", [])

                    if not context_items:
                        return ""

                    dlogger.info(
                        f"[CTX_FETCH_SUCCESS] {len(context_items)} memories retrieved"
                    )

                    cleaned = []

                    for i, item in enumerate(context_items):

                        text = item.get("text", "").strip()
                        score = item.get("score")
                        ts = item.get("timestamp")

                        if not text:
                            continue

                        snippet = text.replace("\n", " ")[:120]

                        dlogger.debug(
                            f"[CTX_{i+1}] score={score} ts={ts} text='{snippet}...'"
                        )

                        cleaned.append(text)

                    # VRAM-safe memory limit
                    MAX_MEMORY_CHARS = 1000

                    context_text = "\n".join(cleaned)

                    if len(context_text) > MAX_MEMORY_CHARS:
                        context_text = context_text[:MAX_MEMORY_CHARS]

                    return context_text

        except Exception as e:
            dlogger.warning(f"[CONTEXT_FAIL] {e}")
            return ""

    context_text = await get_chat_context()

    # ────────────────────────────────────────────────
    # STEP 1.5 — Assemble Final Prompt
    # ────────────────────────────────────────────────

    sections = []

    # SYSTEM INSTRUCTION
    if instruction and instruction.strip():
        sections.append(f"[SYSTEM]\n{instruction.strip()}")

    # VECTOR MEMORY
    if context_text and context_text.strip():
        sections.append(f"[MEMORY]\n{context_text.strip()}")

    # ROLLING CONTEXT WINDOW
    if history_text and history_text.strip():
        sections.append(f"[RECENT CHAT]\n{history_text.strip()}")

    # CURRENT USER MESSAGE
    sections.append(f"[USER]\n{prompt}")

    full_prompt = "\n\n".join(sections)

    # ────────────────────────────────────────────────
    # Prompt Safety Guard
    # ────────────────────────────────────────────────

    MAX_PROMPT_CHARS = 2000

    if len(full_prompt) > MAX_PROMPT_CHARS:
        dlogger.warning("[PROMPT_TRIM] Prompt exceeded safe limit. Trimming.")
        full_prompt = full_prompt[-MAX_PROMPT_CHARS:]

    dlogger.debug(
        f"[PROMPT_STATS] total_chars={len(full_prompt)} "
        f"memory_chars={len(context_text)} "
        f"history_chars={len(history_text)}"
    )

    # ────────────────────────────────────────────────
    # STEP 2 — Send to WebSocket Runtime
    # ────────────────────────────────────────────────
    if stream:
        # STREAMING MODE
        async def stream_tokens():
            collected = []
            for attempt in range(30):
                try:
                    async with websockets.connect(uri) as ws:
                        await ws.send(json.dumps({"prompt": full_prompt, "stream": True}))
                        async for msg in ws:
                            data = json.loads(msg)
                            if "token" in data:
                                token = data["token"]
                                collected.append(token)

                                global last_generation_activity
                                last_generation_activity = time.time()

                                yield token
                            elif data.get("done"):
                                break
                        break
                except (ConnectionRefusedError, OSError):
                    await asyncio.sleep(1)
                    continue
                except Exception as e:
                    dlogger.error(f"[WS_STREAM_FAIL] {type(e).__name__}: {e}")
                    yield f"[WebSocket Error] {e}"
                    return

            # ────────────────────────────────────────────────
            # STEP 3 — Save Chat (Background)
            # ────────────────────────────────────────────────

            full_reply = "".join(collected).strip()

            global generation_active, last_generation_end

            generation_active = False
            last_generation_activity = time.time()

            async def save_chats():

                try:

                    now = time.time()

                    payloads = [
                        {
                            "role": "user",
                            "content": prompt,
                            "session_id": session_id,
                            "source": "chat",
                            "timestamp": now,
                            "importance": 1.0
                        },
                        {
                            "role": "assistant",
                            "content": full_reply,
                            "session_id": session_id,
                            "source": "chat",
                            "timestamp": now,
                            "importance": 0.7
                        }
                    ]

                    async with aiohttp.ClientSession() as session:

                        for payload in payloads:

                            await session.post(
                                f"{EMBEDDER_API}/chat/add",
                                json=payload
                            )

                    dlogger.info(
                        f"[MEMORY] Stored chat pair session={session_id} "
                        f"user_chars={len(prompt)} assistant_chars={len(full_reply)}"
                    )

                except Exception as e:

                    dlogger.warning(f"[MEMORY_SAVE_FAIL] {e}")

            # Fire-and-forget background save
            asyncio.create_task(save_chats())

            global restart_after_generation

            if restart_after_generation:

                dterminal(
                    "[WATCHDOG] Restarting runtime after generation completion.",
                    level="INFO"
                )

                restart_after_generation = False

                stop_dml_runtime()
                start_dml_runtime()

        return StreamingResponse(stream_tokens(), media_type="text/plain")

    else:
        # NON-STREAMING MODE
        output = None
        for attempt in range(30):
            try:
                async with websockets.connect(uri) as ws:
                    await ws.send(json.dumps({"prompt": full_prompt, "stream": False}))
                    msg = await ws.recv()
                    data = json.loads(msg)
                    output = data.get("full_reply") or data.get("reply") or "[No output]"
                    break
            except (ConnectionRefusedError, OSError):
                await asyncio.sleep(1)
                continue
            except Exception as e:
                dlogger.error(f"[WS_FAIL] {type(e).__name__}: {e}")
                raise HTTPException(status_code=500, detail=f"WebSocket error: {e}")
        else:
            raise HTTPException(status_code=504, detail="DirectML WebSocket runtime not responding.")

        dlogger.info(f"[DISH_OUTPUT] {output}")

        generation_active = False
        last_generation_activity = time.time()

        # ────────────────────────────────────────────────
        # STEP 3 — Save Chat Messages to Embedder
        # ────────────────────────────────────────────────
        try:
            now = time.time()
            payloads = [
                {
                    "role": "user",
                    "content": prompt,
                    "session_id": session_id,
                    "source": "chat",
                    "timestamp": now,
                    "importance": 1.0
                },
                {
                    "role": "assistant",
                    "content": output,
                    "session_id": session_id,
                    "source": "chat",
                    "timestamp": now,
                    "importance": 0.7
                }
            ]

            async with aiohttp.ClientSession() as session:
                for payload in payloads:
                    await session.post(
                        f"{EMBEDDER_API}/chat/add",
                        json=payload
                    )

            dlogger.info(
                f"[MEMORY] Stored chat pair session={session_id} "
                f"user_chars={len(prompt)} assistant_chars={len(output)}"
            )
        except Exception as e:
            dlogger.warning(f"[MEMORY_SAVE_FAIL] {e}")

        global restart_after_generation

        if restart_after_generation:

            dterminal(
                "[WATCHDOG] Restarting runtime after generation completion.",
                level="INFO"
            )

            restart_after_generation = False

            stop_dml_runtime()
            start_dml_runtime()

        return {
            "status": "success",
            "input": prompt,
            "reply": output
        }

# @ui_group "Instruction Block"
# @ui_zone "diag"
# @ui_key diag.dish.instruction.01
# @ui instructionblock