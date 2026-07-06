# functions.py — DISH Document Parser Router
import os
import tempfile
from typing import Dict, Any
from pydantic import BaseModel
from dev.diagnostics import get_logger
from fastapi import UploadFile, File, APIRouter, HTTPException, Request
from app.modules.Data_Parser.dish_parse import parse_document, save_parsed_json

# ──────────────────────────────────────────────────────────────
# Setup
router = APIRouter()
plogger = get_logger("data_parser.functions")
last_parsed_data: Dict[str, Any] = {}

# ──────────────────────────────────────────────────────────────
# Utility Helpers
def sanitize_chunks(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all chunks are UTF-8 safe for frontend rendering."""
    parsed["chunks"] = [
        {
            "chunk": str(c.get("chunk", "")).encode("utf-8", "ignore").decode("utf-8"),
            "meta": c.get("meta", {}),
        }
        for c in parsed.get("chunks", [])
    ]
    return parsed

# ──────────────────────────────────────────────────────────────
# Request Models
class FilePathRequest(BaseModel):
    file_path: str

# ──────────────────────────────────────────────────────────────
# Routes

# @ui_group "DISH Display"
# @ui_zone "main"
# @ui_key DISH.sidebar.upload_and_parse
# @ui docbox

@router.post("/document/browse-files")
def browse_files(req: FilePathRequest):
    """
    Returns a list of .txt and .docx files under the requested path.
    Used for server-side browsing of existing files.
    """
    base_path = req.file_path
    plogger.info(f"[BROWSE] Request received for path: {base_path}")
    try:
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"Path does not exist: {base_path}")

        files = []
        for root, _, filenames in os.walk(base_path):
            for name in filenames:
                if name.lower().endswith((".txt", ".docx")):
                    files.append({
                        "name": name,
                        "path": os.path.join(root, name)
                    })

        plogger.info(f"[BROWSE] Found {len(files)} eligible files in {base_path}")
        return {
            "status": "success",
            "reply": {
                "files": files,
                "count": len(files),
                "searched": base_path
            }
        }

    except Exception as e:
        plogger.error(f"[BROWSE_FAIL] {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document/upload_and_parse")
async def upload_and_parse(file: UploadFile = File(...)):
    global last_parsed_data
    plogger.info(f"[UPLOAD_PARSE] Received: {file.filename}")

    try:
        # ─── Validate extension ─────────────────────────────
        ext = os.path.splitext(file.filename)[-1].lower()
        if ext not in [".txt", ".docx"]:
            raise HTTPException(status_code=400, detail="Unsupported file type.")

        # ─── Read contents ──────────────────────────────────
        contents = await file.read()

        if ext == ".txt":
            try:
                contents.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Text file must be UTF-8 encoded.")

        # ─── Sanitize filename ───────────────────────────────
        # remove dangerous characters and spaces
        safe_filename = os.path.basename(file.filename).replace(" ", "_")
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in ("-", "_", "."))
        safe_tmp_path = os.path.join(tempfile.gettempdir(), safe_filename)

        # ─── Write actual filename to temp ───────────────────
        with open(safe_tmp_path, "wb") as tmp:
            tmp.write(contents)

        plogger.info(f"[UPLOAD_PARSE] Temporary file written: {safe_tmp_path}")

        # ─── Parse the document ──────────────────────────────
        parsed = parse_document(safe_tmp_path)
        parsed["filename"] = file.filename  # include original filename
        os.remove(safe_tmp_path)

        # ─── Clean + store in memory ─────────────────────────
        parsed = sanitize_chunks(parsed)
        last_parsed_data = {"reply": parsed}

        plogger.info(f"[UPLOAD_PARSE] Parsed {len(parsed['chunks'])} chunks from {file.filename}")

        return {
            "status": "success",
            "reply": parsed
        }

    except Exception as e:
        plogger.error(f"[UPLOAD_PARSE_FAIL] {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document/trigger-save")
def trigger_save():
    global last_parsed_data

    if not last_parsed_data or "reply" not in last_parsed_data:
        raise HTTPException(status_code=400, detail="No parsed data available to save.")

    parsed = last_parsed_data["reply"]
    filename = parsed.get("filename", "unknown_file")
    plogger.info(f"[TRIGGER_SAVE] Saving parsed data: {filename}")

    try:
        if "chunks" not in parsed or not isinstance(parsed["chunks"], list):
            raise ValueError("Invalid data format — missing 'chunks' array.")

        # 💾 Save locally
        save_parsed_json(parsed)

        # ✅ Embed & inject into vectorstore
        texts = [c["chunk"] for c in parsed["chunks"]]
        metadatas = [c["meta"] for c in parsed["chunks"]]
        vector_count = len(texts)

        embedder_url = os.getenv("EMBEDDER_API_URL", "http://127.0.0.1:8007")
        endpoint = f"{embedder_url}/db/add"
        plogger.debug(f"[VECTOR_PUSH] Target: {endpoint} | Chunks: {vector_count}")

        import requests
        try:
            response = requests.post(endpoint, json={
                "texts": texts,
                "metadatas": metadatas
            })
            response.raise_for_status()
            embed_result = response.json().get("added", 0)
        except Exception as embed_err:
            plogger.error(f"[VECTOR_PUSH_FAIL] {type(embed_err).__name__}: {embed_err}")
            raise HTTPException(status_code=500, detail=f"Embedding push failed: {embed_err}")

        plogger.info(f"[TRIGGER_SAVE] Embedder injected {embed_result} vector entries.")

        return {
            "status": "success",
            "reply": {
                "message": f"Parsed data saved and embedded. {embed_result} chunks written.",
                "filename": filename,
                "hash_id": parsed.get("hash_id", "unknown"),
                "chunk_count": embed_result,
                "metadata": parsed.get("metadata", {}),
            },
        }

    except Exception as e:
        plogger.error(f"[TRIGGER_SAVE_FAIL] {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))






