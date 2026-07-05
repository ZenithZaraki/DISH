# ============================================================
# DISH-Core Minimal Runtime (DirectML Edition) — Enhanced Logs
# ============================================================
import os
import sys
import json
import asyncio
import threading
import queue
import websockets

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from dev.diagnostics import terminal_alert, get_logger

# ---------------- CONFIG ----------------
GPU_INDEX = 1
USE_COMPILE = True
MAX_NEW_TOKENS = 512
USE_CPU = os.environ.get("DISH_FORCE_CPU", "0") == "1"
logger = get_logger("Test_APM.DishRuntime")

terminal_alert("=" * 60, level="INFO")
terminal_alert("DISH-Core DirectML Runtime Booting...", level="INFO")
terminal_alert("=" * 60, level="INFO")
logger.info("Runtime boot initialized — DirectML mode")

# ---------------- ENVIRONMENT ----------------
os.environ["DML_EXECUTION_MODE"] = "0"        # Force eager mode for safety
os.environ["DML_VISIBLE_DEVICES"] = str(GPU_INDEX)
os.environ["CUDA_VISIBLE_DEVICES"] = ""       # Disable CUDA entirely

# ---------------- IMPORT DML ----------------
LOCAL_DML_DEPS = os.path.join(os.path.dirname(__file__), "local_deps", "torch_directml")

if LOCAL_DML_DEPS not in sys.path:
    sys.path.insert(0, LOCAL_DML_DEPS)

import torch
import torch_directml

import transformers.models.phi3.modeling_phi3 as phi3_mod
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer

torch.set_float32_matmul_precision("medium")
torch.set_num_threads(20)
torch.set_num_interop_threads(20)

# ---------------- PATCH: RoPE for DirectML ----------------
def _rotate_half(x: torch.Tensor) -> torch.Tensor:
    x1 = x[..., : x.shape[-1] // 2]
    x2 = x[..., x.shape[-1] // 2 :]
    return torch.cat((-x2, x1), dim=-1)

def apply_rotary_pos_emb_dml_safe(q, k, cos, sin, position_ids=None, unsqueeze_dim=1):
    q, k = q.contiguous(), k.contiguous()
    cos, sin = cos.unsqueeze(unsqueeze_dim).contiguous(), sin.unsqueeze(unsqueeze_dim).contiguous()
    q32, k32, cos32, sin32 = q.float(), k.float(), cos.float(), sin.float()
    q_embed = (q32 * cos32) + (_rotate_half(q32) * sin32)
    k_embed = (k32 * cos32) + (_rotate_half(k32) * sin32)
    return q_embed.to(q.dtype), k_embed.to(k.dtype)

phi3_mod.apply_rotary_pos_emb = apply_rotary_pos_emb_dml_safe
terminal_alert("[PATCH] RoPE DirectML patch applied", level="INFO")
logger.info("RoPE patched for DirectML compatibility")

# ============================================================
#  RUNTIME CLASS
# ============================================================
class DishRuntime:
    def __init__(self):
        # -------------------------
        # DEVICE SELECTION (CPU vs DML)
        # -------------------------
        if USE_CPU:
            self.device = torch.device("cpu")
            terminal_alert("[DEVICE] CPU MODE ENABLED — DirectML bypassed", level="WARN")
            logger.info("Runtime device: CPU")
        else:
            self.device = torch_directml.device(GPU_INDEX)
            name = torch_directml.device_name(GPU_INDEX)
            terminal_alert(f"[GPU] Using DirectML device -> {name}", level="INFO")
            logger.info(f"DirectML Device: {name}")

        # -------------------------
        # RUNTIME STATE
        # -------------------------
        self.model = None
        self.tokenizer = None
        self.stop_flag = threading.Event()
        self.gen_thread = None
        self.streamer = None
        self.use_compile = USE_COMPILE

        # Metroscope handle (created after model load)
        self.scope = None

    # --------------------------------------------------------
    # LOAD MODEL
    # --------------------------------------------------------
    def load_model(self, model_path: str = None):
        if self.model is not None:
            msg = "[LOAD] Model already loaded — skipping reload."
            terminal_alert(msg, level="WARN")
            logger.warning(msg)
            return

        if not model_path:
            model_path = os.path.join(
                os.path.dirname(__file__),
                "models",
                "Phi-3.5-mini-instruct"
            )
        model_path = os.path.abspath(model_path)

        terminal_alert(f"[LOAD] Loading model from {model_path}", level="INFO")
        logger.info(f"Loading model from path: {model_path}")

        try:
            # MODEL LOADING IS AUTOMATICALLY DEVICE-AWARE
            dtype = torch.float16 if not USE_CPU else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path,
                dtype=dtype,
                attn_implementation="eager",
            ).to(self.device)

            # --- Runtime generation defaults ---
            # Keep attentions disabled during normal generation.
            # DirectML can become slow or unstable when attention tensors are requested.
            # Enable this only when Metroscope/attention inspection explicitly needs it.
            self.model.config.output_attentions = False
            self.model.config.output_hidden_states = False
            self.model.config.use_cache = True

            # Precision logging
            precision = "fp16" if not USE_CPU else "fp32"
            logger.info(f"Model precision set to {precision}")
            terminal_alert(f"[LOAD] Model precision: {precision}", level="INFO")

            # CPU sanity check
            if USE_CPU:
                assert self.model.dtype == torch.float32, \
                    "CPU mode requires FP32 - model loaded with incorrect precision."

            if self.use_compile:
                self.model = torch.compile(
                    self.model,
                    backend="inductor",
                    mode="max-autotune",
                    dynamic=True
                )
                terminal_alert("[LOAD] Torch compile optimization applied.", level="INFO")
                logger.info("Torch compile optimization applied")

        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            terminal_alert(f"[ERROR] Failed to load model: {e}", level="ERROR")
            raise

        # Configure tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
        self.tokenizer.truncation_side = "left"

        terminal_alert(f"[READY] Model loaded from {model_path}", level="SUCCESS")
        logger.info("Tokenizer configured and model ready")

    # --------------------------------------------------------
    # GENERATION
    # --------------------------------------------------------
    def generate(self, prompt, stream_callback=None, max_new_tokens=MAX_NEW_TOKENS):
        if not self.model:
            terminal_alert("[ERROR] No model loaded", level="ERROR")
            logger.error("Attempted generation with no model loaded")
            return ""

        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(self.device)

        self.streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            timeout=120
        )
        self.stop_flag.clear()

        stop_sequences = [
            "\nUser:",
            "\nAssistant:",
            "\nSystem:",
            "User:",
            "Assistant:",
            "System:"
        ]

        def worker():
            with torch.no_grad():
                try:
                    self.model.generate(
                        **inputs,
                        streamer=self.streamer,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        use_cache=True,
                        temperature=0.8,
                        top_k=30,
                        top_p=0.92,
                        pad_token_id=self.tokenizer.pad_token_id,
                        eos_token_id=self.tokenizer.eos_token_id,
                    )
                except Exception as e:
                    terminal_alert(f"[GEN] Error: {e}", level="ERROR")
                    logger.error(f"Generation thread failed: {e}")
                    try:
                        self.streamer.end()
                    except Exception:
                        pass

        self.gen_thread = threading.Thread(target=worker, daemon=True)
        self.gen_thread.start()

        output = ""
        streamed_length = 0

        try:
            for chunk in self.streamer:
                if self.stop_flag.is_set():
                    break

                output += chunk

                stop_hit = None
                for seq in stop_sequences:
                    idx = output.find(seq)
                    if idx != -1:
                        stop_hit = idx
                        break

                if stop_hit is not None:
                    output = output[:stop_hit]
                    self.stop_flag.set()
                    break

                new_text = output[streamed_length:]
                if new_text and stream_callback:
                    stream_callback(new_text)
                streamed_length = len(output)

        except queue.Empty:
            logger.error("Generation streamer timed out before receiving output")
            terminal_alert("[GEN] Streamer timed out before receiving output", level="ERROR")

        if self.gen_thread and self.gen_thread.is_alive():
            self.gen_thread.join(timeout=1)

        logger.info("Full generation output returned")
        return output.strip()

    def stop_generation(self):
        if self.stop_flag.is_set():
            return
        self.stop_flag.set()
        if self.gen_thread and self.gen_thread.is_alive():
            self.gen_thread.join(timeout=1)
        self.gen_thread = None
        terminal_alert("[GEN] Stop requested — generation halted.", level="WARN")
        logger.warning("Streaming halted by stop signal")

    def _torch_gc(self):
        import gc, time

        logger.info("[GC] Running garbage collection and memory flush")

        gc.collect()

        try:
            import torch_directml
            torch_directml._destroy_dml_allocator()
        except Exception:
            pass

        try:
            _ = torch.empty(1, device=self.device)
            del _
        except Exception as e:
            logger.warning(f"[GC] Allocator flush skipped: {e}")

        time.sleep(0.05)

    def _handle_oom(self, context="unknown"):
        logger.warning(f"[OOM] Out of memory detected during: {context}")
        terminal_alert(f"[OOM] OOM in {context} — clearing memory", level="ERROR")
        self.stop_generation()
        self._torch_gc()

# ============================================================
#  WEBSOCKET SERVER
# ============================================================
runtime = DishRuntime()

async def handle_client(websocket):
    logger.info("Client connected to DirectML WebSocket runtime")
    await websocket.send(json.dumps({"status": "ready"}))
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    try:
        runtime.load_model()
    except Exception as e:
        error_msg = f"Model failed to load: {e}"
        logger.error(error_msg)
        await websocket.send(json.dumps({"error": error_msg}))
        return

    async for message in websocket:
        try:
            data = json.loads(message)

            if data.get("cmd") == "stop":
                runtime.stop_generation()
                stop_event.set()
                await websocket.send(json.dumps({"status": "stopped"}))
                logger.info("Stop command handled via WebSocket")
                continue

            prompt = data.get("prompt", "").strip()
            if not prompt:
                await websocket.send(json.dumps({"error": "Empty prompt received"}))
                logger.warning("Empty prompt received — ignoring request")
                continue

            stop_event.clear()

            def token_streamer(token):
                if not stop_event.is_set():
                    try:
                        loop.call_soon_threadsafe(
                            asyncio.create_task,
                            websocket.send(json.dumps({"token": token}))
                        )
                    except Exception as e:
                        logger.warning(f"Token send failed: {e}")

            # Wrap generation with OOM protection
            try:
                output = await loop.run_in_executor(
                    None,
                    lambda: runtime.generate(prompt, stream_callback=token_streamer)
                )
            except RuntimeError as oom:
                if "out of memory" in str(oom).lower():
                    runtime._handle_oom(context="generation")
                    await websocket.send(json.dumps({"error": "Out of memory during generation"}))
                    continue
                else:
                    logger.error(f"Unhandled generation error: {oom}")
                    await websocket.send(json.dumps({"error": str(oom)}))
                    continue

            await websocket.send(json.dumps({"done": True, "full_reply": output}))
            logger.info("Streaming session completed and sent")

        except Exception as e:
            logger.warning(f"WebSocket error: {e}")
            try:
                await websocket.send(json.dumps({"error": str(e)}))
            except:
                logger.warning("WebSocket closed before error could be sent")

async def start_server():
    terminal_alert("[DISH] Initializing DirectML runtime...", level="INFO")
    logger.info("Starting DirectML WebSocket server")

    try:
        runtime.load_model()
        terminal_alert("[DISH] Model preloaded successfully.", level="SUCCESS")
    except Exception as e:
        terminal_alert(f"[DISH] Failed to load model: {e}", level="ERROR")
        logger.error(f"Runtime load_model() failed: {e}")
        raise

    async with websockets.serve(handle_client, "127.0.0.1", 8765):
        terminal_alert("[DISH] DirectML runtime WebSocket active on port 8765", level="INFO")
        logger.info("WebSocket server now accepting clients")
        await asyncio.Future()

if __name__ == "__main__":
    terminal_alert("[DISH] Starting DirectML WebSocket runtime...", level="INFO")
    try:
        asyncio.run(start_server())
    except Exception as e:
        logger.error(f"Fatal crash during runtime: {e}")
        terminal_alert(f"[FATAL] {e}", level="ERROR")
