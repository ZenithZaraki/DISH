# ============================================================
# embedder_worker.py — DirectML Async Embedder + Vector Store
# ============================================================
import os
import sys
import time
import uuid
import shutil
import hashlib
import asyncio
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
from dev.diagnostics import terminal_alert, get_logger

# ─── FastAPI + Logging Setup ────────────────────────────────
app = FastAPI()
wlogger = get_logger("Test_APM.embedder_worker")
wterminal_alert = terminal_alert

# ─── Environment Setup ─────────────────────────────────────
base = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(base, "local_deps", "embedder_DML"))
import numpy as np
import onnxruntime as ort
terminal_alert(ort.get_available_providers(), level="INFO")
from langchain_chroma import Chroma
from transformers.onnx import export
from onnxruntime import InferenceSession
from langchain.embeddings.base import Embeddings
from transformers import AutoTokenizer, AutoModel
from transformers.onnx.features import FeaturesManager

# ─── Paths & Config ─────────────────────────────────────────
base = os.path.abspath(os.path.dirname(__file__))

MODEL_NAME = "intfloat/e5-small-v2"
MODEL_DIR = os.path.join(base, "memory_cache", "models--intfloat--e5-small-v2")
MODEL_PATH = os.path.join(base, "onnx_models", "e5-small-v2-onnx")   # exported once
CACHE_DIR = os.path.join(base, "memory_cache")
VECTOR_DB_PATH = os.path.join(base, "vector_store")

# ─── Auto-build safeguard ──────────────────────────────────
def ensure_onnx_model():
    """
    Ensure ONNX model exists; rebuild if missing or corrupted.
    IMPORTANT: Directly export ONNX model to MODEL_PATH without using temp files.
    """

    # Ensure ONNX output directory exists
    onnx_out_dir = os.path.dirname(MODEL_PATH)
    os.makedirs(onnx_out_dir, exist_ok=True)

    # Skip rebuild if model already exists
    if os.path.exists(MODEL_PATH):
        wlogger.info(f"[ONNX] Found existing model: {MODEL_PATH}")
        return

    try:
        wlogger.warning(f"[ONNX] Model missing at {MODEL_PATH} — rebuilding from {MODEL_NAME}...")

        # Load model/tokenizer from HF cache
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModel.from_pretrained(MODEL_NAME)

        # Determine ONNX export config
        kind, onnx_config_cls = FeaturesManager.check_supported_model_or_raise(model)
        onnx_config = onnx_config_cls(model.config)

        # Export ONNX model directly to the final path (overwrite-safe)
        export(
            preprocessor=tokenizer,
            model=model,
            config=onnx_config,
            opset=17,
            output=Path(onnx_out_dir),
        )

        # Rename output/model.onnx to desired MODEL_PATH
        exported_path = os.path.join(onnx_out_dir, "model.onnx")
        if not os.path.exists(exported_path):
            raise FileNotFoundError(f"[ONNX] Exported model not found at {exported_path}")

        os.replace(exported_path, MODEL_PATH)
        wlogger.info(f"[ONNX] Conversion complete -> {MODEL_PATH}")
        wterminal_alert(f"[ONNX] Conversion complete -> {MODEL_PATH}", level="INFO")

    except PermissionError as e:
        wlogger.critical(f"[ONNX_INIT_FAIL] Permission denied: {e}")
        wterminal_alert(f"[ONNX_INIT_FAIL] Permission denied: {e}", level="ERROR")
        raise

    except Exception as e:
        wlogger.exception(f"[ONNX_INIT_FAIL] Unexpected error: {e}")
        wterminal_alert(f"[ONNX_INIT_FAIL] Unexpected error: {e}", level="ERROR")
        raise

# Valid options: "cpu", "gpu0", "gpu1", etc.
# ─── Device Selection & Provider Setup ───────────────────────
DEVICE = os.getenv("DISH_DEVICE", "gpu1").lower()

available_providers = ort.get_available_providers()
wlogger.info(f"[ONNX] System available providers: {available_providers}")

if DEVICE == "cpu":
    providers = ["CPUExecutionProvider"]
elif DEVICE.startswith("gpu"):
    try:
        gpu_id = int(DEVICE[3:])
    except ValueError:
        gpu_id = 0

    if "DmlExecutionProvider" in available_providers:
        providers = [("DmlExecutionProvider", {"device_id": gpu_id}), "CPUExecutionProvider"]
    else:
        wlogger.warning("[ONNX] DmlExecutionProvider not available! Falling back to CPU.")
        providers = ["CPUExecutionProvider"]
else:
    raise ValueError(f"Invalid DISH_DEVICE: {DEVICE}. Use 'cpu', 'gpu0', 'gpu1', etc.")

# ─── Initialize ONNX Session ────────────────────────────────
try:
    ensure_onnx_model()

    session = ort.InferenceSession(MODEL_PATH, providers=providers)
    active_providers = session.get_providers()
    opts = session.get_provider_options()

    wlogger.info(f"[ONNX] Providers active: {active_providers}")
    wlogger.info(f"[ONNX] Provider options: {opts}")
    wterminal_alert(f"[ONNX] Active: {active_providers} | Options: {opts}", level="INFO")

    USE_GPU = "DmlExecutionProvider" in active_providers
except Exception as e:
    session = None
    USE_GPU = False
    wlogger.error(f"[ONNX_INIT_FAIL] {e}")
    wterminal_alert(f"[ONNX_INIT_FAIL] {e}", level="CRITICAL")

# ─── Tokenizer ──────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


# ─── Embedding Wrapper Class ────────────────────────────────

class ONNXEmbedder(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return embed_texts(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        return embed_texts(text)[0].tolist()

# ─── Vector DB (optional) ───────────────────────────────────
vector_store = None
if os.path.exists(VECTOR_DB_PATH):
    try:
        vector_store = Chroma(
            embedding_function=ONNXEmbedder(),  # ← proper interface
            persist_directory=VECTOR_DB_PATH
        )
        wlogger.info("[VECTOR_DB] Loaded existing Chroma store.")
    except Exception as e:
        wlogger.warning(f"[VECTOR_DB_FAIL] {e}")

# ─── Embedding Helper ───────────────────────────────────────
def embed_texts(texts):
    """Run ONNX inference and return normalized float32 embeddings."""
    if session is None:
        raise RuntimeError("ONNX session not initialized")

    if isinstance(texts, str):
        texts = [texts]

    # Tokenize on CPU
    tokens = tokenizer(texts, padding=True, truncation=True, return_tensors="np")
    ort_inputs = {
        "input_ids": tokens["input_ids"].astype(np.int64),
        "attention_mask": tokens["attention_mask"].astype(np.int64),
    }

    # Inference on GPU (DirectML)
    outputs = session.run(["last_hidden_state"], ort_inputs)
    embeddings = np.mean(outputs[0], axis=1)  # mean pooling
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.clip(norms, 1e-9, None)

    return embeddings.astype(np.float32)

# ─── Async Wrappers ─────────────────────────────────────────
async def _run_async(func, *args):
    return await asyncio.to_thread(func, *args)

def _text_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

# ─── Endpoints ──────────────────────────────────────────────
@app.get("/ping")
async def ping():
    return {
        "status": "READY" if session else "FAILED",
        "backend": "ONNXRuntime (DirectML)" if USE_GPU else "ONNXRuntime (CPU)",
        "vector_db": "READY" if vector_store else "UNAVAILABLE",
    }

@app.post("/task/query")
async def embed_query(text: str = Body(..., embed=True)):
    try:
        start = time.time()
        vec = embed_texts(text)[0].tolist()
        elapsed = time.time() - start
        wlogger.info(f"[EMBED_QUERY] dim={len(vec)} | {elapsed:.3f}s")
        return {"vector": vec, "elapsed": elapsed}
    except Exception as e:
        wlogger.error(f"[EMBED_QUERY_FAIL] {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/task/documents")
async def embed_documents(texts: list[str] = Body(..., embed=True)):
    try:
        texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
        if not texts:
            return {"vectors": []}
        start = time.time()
        vecs = embed_texts(texts).tolist()
        elapsed = time.time() - start
        wlogger.info(f"[EMBED_DOCS] {len(texts)} docs | {elapsed:.2f}s")
        return {"vectors": vecs, "elapsed": elapsed}
    except Exception as e:
        wlogger.error(f"[EMBED_DOCS_FAIL] {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/db/add")
async def add_to_db(payload: dict = Body(...)):
    if vector_store is None:
        wlogger.warning("[VECTOR_DB_MISSING] Vector store not initialized.")
        return JSONResponse(content={"error": "Vector DB not initialized"}, status_code=503)
    try:
        texts = payload.get("texts", [])
        metas = payload.get("metadatas", [{}] * len(texts))

        if not texts:
            wlogger.warning("[VECTOR_ADD_EMPTY] No texts provided.")
            return {"added": 0}

        if len(metas) != len(texts):
            raise ValueError(f"Mismatch: {len(texts)} texts vs {len(metas)} metadatas")

        def split_into_chunks(text, max_tokens=200):
            import re
            sentences = re.split(r'(?<=[.?!])\s+', text)
            chunks, current = [], []
            count = 0

            for sent in sentences:
                tokens = tokenizer.encode(sent)
                if count + len(tokens) > max_tokens:
                    if current:
                        chunks.append(" ".join(current))
                        current, count = [], 0
                current.append(sent)
                count += len(tokens)

            if current:
                chunks.append(" ".join(current))

            return chunks

        chunked_texts = []
        chunked_metas = []

        for i, text in enumerate(texts):
            meta = metas[i]
            chunks = split_into_chunks(text)
            for idx, chunk in enumerate(chunks):
                new_meta = dict(meta)
                new_meta["chunk_index"] = idx
                chunked_texts.append(chunk)
                chunked_metas.append(new_meta)

        wlogger.info(f"[VECTOR_ADD] Adding {len(chunked_texts)} chunks (from {len(texts)} original texts)")

        await _run_async(vector_store.add_texts, chunked_texts, chunked_metas)

        if hasattr(vector_store, "persist") and callable(vector_store.persist):
            await _run_async(vector_store.persist)
        else:
            wlogger.debug("[VECTOR_DB] Persist skipped (not available)")

        wlogger.info(f"[VECTOR_DB] Successfully added {len(chunked_texts)} vector entries.")
        return {"added": len(chunked_texts)}

    except Exception as e:
        wlogger.error(f"[VECTOR_ADD_FAIL] {type(e).__name__}: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/db/query")
async def query_db(payload: dict = Body(...)):
    if vector_store is None:
        return {"error": "Vector DB not initialized"}
    try:
        query = payload.get("query", "")
        session_id = payload.get("session_id")  # Optional
        k = payload.get("k", 5)

        # Run similarity search
        results = await _run_async(vector_store.similarity_search, query, k)

        # Optional filtering by session_id
        if session_id:
            filtered = [
                {"text": r.page_content, "metadata": r.metadata}
                for r in results
                if r.metadata.get("session_id") == session_id
            ]
            wlogger.info(f"[DB_QUERY] Filtered {len(filtered)} results by session_id={session_id}")
            return {"results": filtered}
        else:
            unfiltered = [
                {"text": r.page_content, "metadata": r.metadata}
                for r in results
            ]
            wlogger.info(f"[DB_QUERY] Retrieved {len(unfiltered)} unfiltered results")
            return {"results": unfiltered}

    except Exception as e:
        wlogger.error(f"[DB_QUERY_FAIL] {e}")
        wlogger.debug(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/chat/add")
async def add_chat_message(payload: dict = Body(...)):
    if vector_store is None:
        return {"error": "Vector DB not initialized"}
    try:
        text = payload.get("content", "").strip()
        if len(text) < 8:
            return {"added": 0, "session_id": session_id}
        role = payload.get("role", "user")
        session_id = payload.get("session_id") or str(uuid.uuid4())
        if not text:
            return {"added": 0, "session_id": session_id}

        # Split assistant messages into smaller chunks (~200 tokens)
        def split_into_chunks(text, max_tokens=200):
            import re
            sentences = re.split(r'(?<=[.?!])\s+', text)
            chunks, current = [], []
            count = 0

            for sent in sentences:
                tokens = tokenizer.encode(sent)
                if count + len(tokens) > max_tokens:
                    if current:
                        chunks.append(" ".join(current))
                        current, count = [], 0
                current.append(sent)
                count += len(tokens)

            if current:
                chunks.append(" ".join(current))

            return chunks

        if role == "assistant":
            chunks = split_into_chunks(text)
            metadatas = [{
                "role": role,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "importance": payload.get("importance", 0.7),
                "source": payload.get("source", "chat"),
                "chunk_index": i
            } for i in range(len(chunks))]

            await _run_async(vector_store.add_texts, chunks, metadatas)
            wlogger.info(f"[CHAT_LOG] Stored assistant reply as {len(chunks)} vector chunks")
            return {"added": len(chunks), "session_id": session_id}
        else:
            metadata = {
                "role": role,
                "session_id": session_id,
                "timestamp": payload.get("timestamp", time.time()),
                "importance": payload.get("importance", 0.5),
                "source": payload.get("source", "chat"),
            }
            await _run_async(vector_store.add_texts, [text], [metadata])
            wlogger.info(f"[CHAT_LOG] Stored user message for session {session_id}")
            return {"added": 1, "session_id": session_id}

    except Exception as e:
        wlogger.error(f"[CHAT_ADD_FAIL] {e}")
        wlogger.debug(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/chat/context")
async def get_chat_context(payload: dict = Body(...)):
    if vector_store is None:
        return {"error": "Vector DB not initialized"}
    try:
        session_id = payload.get("session_id")
        query = payload.get("query", "")
        k = payload.get("k", 3)

        # Run similarity search
        results = await _run_async(vector_store.similarity_search_with_score, query, k * 4)

        now = time.time()
        rescored = []

        for doc, similarity in results:

            meta = doc.metadata

            if meta.get("session_id") != session_id:
                continue

            timestamp = meta.get("timestamp")
            importance = meta.get("importance", 0.5)

            recency = 0
            if timestamp:
                age = now - float(timestamp)
                recency = max(0, 1 - age / 86400)

            final_score = similarity + recency + importance

            rescored.append((final_score, doc))

        rescored.sort(reverse=True)

        filtered = [
            {"text": doc.page_content, "metadata": doc.metadata}
            for _, doc in rescored[:k]
        ]

        # Compose context string for logging
        context_lines = [f"[{i+1}] {r['text']}" for i, r in enumerate(filtered)]
        context_text = "\n".join(context_lines)

        wlogger.info(f"[MEMORY_CONTEXT] Retrieved top {len(filtered)} results for session_id={session_id}")
        wlogger.debug(f"[MEMORY_CONTEXT_RAW]\n{context_text}")

        return {"context": filtered}
    except Exception as e:
        wlogger.error(f"[CHAT_CONTEXT_FAIL] {e}")
        wlogger.debug(traceback.format_exc())
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ─── Entry Point ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("embedder_worker:app", host="127.0.0.1", port=8007, reload=False)