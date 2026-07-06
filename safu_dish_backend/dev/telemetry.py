# telemetry.py
import os
import re
import json
import logging
import datetime as pydatetime
import threading
import queue
import time


WRITE_BUFFER = queue.Queue()
WRITER_RUNNING = False
TELEMETRY_CATEGORIES = ["sys", "calc", "input", "output"]
_telemetry_loggers = {}


def start_writer_thread():
    global WRITER_RUNNING
    if WRITER_RUNNING:
        return

    WRITER_RUNNING = True

    def writer():
        batch = []
        last_flush = time.time()
        FLUSH_INTERVAL = 0.2   # seconds
        MAX_BATCH = 500        # entries

        while WRITER_RUNNING:
            try:
                item = WRITE_BUFFER.get(timeout=0.05)
                batch.append(item)
            except queue.Empty:
                pass

            now = time.time()
            if len(batch) >= MAX_BATCH or (now - last_flush) >= FLUSH_INTERVAL:
                _flush_batch(batch)
                batch = []
                last_flush = now

    threading.Thread(target=writer, daemon=True).start()


def _flush_batch(batch):
    if not batch:
        return

    # Group entries by file path
    groups = {}
    for path, payload in batch:
        groups.setdefault(path, []).append(payload)

    # Write groups
    for path, items in groups.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for line in items:
                f.write(line + "\n")

# ============================================================
# BASE DIRECTORY
# ============================================================

def get_log_base_dir():
    dish_root = os.environ.get("DISH_ROOT")

    if dish_root:
        return os.path.abspath(os.path.join(dish_root, "safu_dish_backend"))

    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# RUN DIRECTORY
# ============================================================

RUN_ID = pydatetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def get_run_dir(module_name):
    base = get_log_base_dir()
    safe_name = module_name.replace(".", os.sep)
    run_dir = os.path.join(base, "telemetry", safe_name, RUN_ID)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir

# ============================================================
# BRACKET PARSER — subsystem, layer, token, tags
# ============================================================

BRACKET_RE = re.compile(
    r'^\['
    r'(?P<subsys>[A-Z0-9_]+)'            # subsystem
    r'(?:\|L(?P<layer>\d+))?'            # optional L#
    r'(?:\|T(?P<token>\d+))?'            # required token format T###
    r'(?P<tags>(?:\|[A-Z][A-Z0-9_]*)*)'  # other tags (H0, etc.)
    r'\]\s*(?P<rest>.*)$'                # metric payload
)

# ============================================================
# METRIC PARSER — preserves lists like [0, 13, 30]
# ============================================================

METRIC_RE = re.compile(
    r'([a-zA-Z_]+)='                     # key
    r'('
    r'\[[^\]]*\]'                        # [0, 13, 30]
    r'|'                                 # OR
    r'\S+'                               # single token (3.14, abc)
    r')'
)

# ============================================================
# STRUCTURED TELEMETRY SORTER — FIXED
# ============================================================

def _sort_structured_telemetry(module_name, record):
    message = getattr(record, "message", "")
    ts = pydatetime.datetime.now().isoformat()

    m = BRACKET_RE.match(message)
    if not m:
        return

    subsystem = m.group("subsys")
    layer     = m.group("layer")
    token_id  = m.group("token")
    raw_tags  = m.group("tags") or ""
    rest      = m.group("rest")

    # Convert numeric fields
    layer = int(layer) if layer else -1
    token_id = int(token_id) if token_id else None

    # ============================================================
    # TAG EXTRACTION — token already stored separately
    # ============================================================
    tags = []
    for t in raw_tags.split("|"):
        t = t.strip()
        if not t:
            continue
        if t.startswith("T"):
            continue
        if t.isdigit():
            continue
        tags.append(t)

    # ============================================================
    # OUTPUT DIRECTORY SETUP
    # ============================================================
    run_dir = get_run_dir(module_name)
    base_dir = os.path.join(run_dir, "structured", subsystem)
    os.makedirs(base_dir, exist_ok=True)

    # This is the NEW output format — JSONL chunks per layer
    out_path = os.path.join(base_dir, f"L{layer}.jsonl")

    # ============================================================
    # BUILD ENTRY
    # ============================================================
    entry = {
        "timestamp": ts,
        "token": token_id,
    }

    if tags:
        entry["tags"] = tags

    # METRIC parsing
    for key, val in METRIC_RE.findall(rest):
        val = val.strip()
        try:
            entry[key] = float(val)
        except ValueError:
            entry[key] = val

    # ============================================================
    # BUFFERED APPEND — NO JSON REWRITE, NO BLOCKING
    # ============================================================
    try:
        line = json.dumps(entry)
        WRITE_BUFFER.put((out_path, line))
    except Exception:
        pass

# ============================================================
# JSONL STREAM HANDLER
# ============================================================

class JSONLTelemetryHandler(logging.Handler):
    def __init__(self, module_name, category_name):
        super().__init__()
        self.category = category_name

        run_dir = get_run_dir(module_name)
        self.file_path = os.path.join(run_dir, f"{category_name}.jsonl")

        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            open(self.file_path, 'w', encoding='utf-8').close()

    def emit(self, record):
        if getattr(record, "category", None) != self.category:
            return

        try:
            line = self.format(record)
            WRITE_BUFFER.put((self.file_path, line))
        except Exception:
            pass

# ============================================================
# FORMATTER
# ============================================================

class TelemetryFormatter(logging.Formatter):
    def format(self, record):
        now = pydatetime.datetime.now().isoformat()
        return json.dumps({
            "timestamp": now,
            "system": record.name,
            "category": record.category,
            "message": record.message
        })

# ============================================================
# TELEMETRY LOGGER
# ============================================================

class TelemetryLogger:

    def __init__(self, module_name):
        self.module_name = module_name

        self.logger = logging.getLogger(f"telemetry.{module_name}")
        self.logger.setLevel(logging.INFO)

        self.handlers = {}

        for cat in TELEMETRY_CATEGORIES:
            handler = JSONLTelemetryHandler(module_name, cat)
            handler.setFormatter(TelemetryFormatter())
            self.logger.addHandler(handler)
            self.handlers[cat] = handler

        self.logger.propagate = False

    def sys(self, message: str):   self._emit("sys", message)
    def calc(self, message: str):  self._emit("calc", message)
    def input(self, message: str): self._emit("input", message)
    def output(self, message: str):self._emit("output", message)

    def _emit(self, category, message):
        try:
            record = self.logger.makeRecord(
                name=self.module_name,
                level=logging.INFO,
                fn='telemetry',
                lno=0,
                msg="",
                args=None,
                exc_info=None
            )

            record.category = category
            record.message = message

            # Write to JSONL
            self.logger.handle(record)

            # Write to structured JSON
            _sort_structured_telemetry(self.module_name, record)

        except Exception:
            pass  # telemetry NEVER fails

# ============================================================
# FACTORY
# ============================================================

def get_telemetry_logger(module_name: str) -> TelemetryLogger:
    if module_name in _telemetry_loggers:
        return _telemetry_loggers[module_name]

    tele = TelemetryLogger(module_name)
    _telemetry_loggers[module_name] = tele
    return tele

start_writer_thread()