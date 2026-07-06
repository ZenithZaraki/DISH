# diagnostics.py
import os
import sys
import json
import hashlib
import logging
import traceback
import datetime as pydatetime
from colorama import Fore, Style
from collections import defaultdict

EVENT_CACHE = defaultdict(lambda: {
    'recent_count': 0,
    'lifetime_count': 0,
    'first_occurred': None,
    'last_occurred': None
})
LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

_loggers = {}

# === LOGGER SETUP ===
def get_log_base_dir():
    dish_root = os.environ.get("DISH_ROOT")

    if dish_root:
        return os.path.abspath(os.path.join(dish_root, "safu_dish_backend"))

    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def _get_log_file_path(module_name, level_name):
    safe_module = module_name.replace('.', os.sep)
    module_log_dir = os.path.join(get_log_base_dir(), "logs", safe_module)
    os.makedirs(module_log_dir, exist_ok=True)
    return os.path.join(module_log_dir, f"{level_name.lower()}.json")

class JSONLogHandler(logging.Handler):
    def __init__(self, module_name, level_name):
        super().__init__()
        self.level_name = level_name
        self.file_path = _get_log_file_path(module_name, level_name)

        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def emit(self, record):
        if record.levelname != self.level_name:
            return

        log_entry = self.format(record)

        try:
            log_data = json.loads(log_entry)
        except json.JSONDecodeError:
            log_data = {
                "event": "LOG_PARSE_FAIL",
                "message": log_entry,
                "level": self.level_name,
                "source": record.name,
                "parse_error": True
            }

        # ─── Stack Trace Injection ─────────────────────────────────
        if self.level_name in ['WARNING', 'ERROR']:
            if record.exc_info:
                log_data["trace"] = ''.join(traceback.format_exception(*record.exc_info))
            elif record.exc_text:
                log_data["trace"] = record.exc_text

        # ─── Update Cache Stats ───────────────────────────────────
        event_key = f"{log_data.get('source')}:{log_data.get('event')}"
        now = pydatetime.datetime.now().isoformat()
        EVENT_CACHE[event_key]['recent_count'] += 1
        EVENT_CACHE[event_key]['lifetime_count'] += 1
        EVENT_CACHE[event_key]['last_occurred'] = now
        if EVENT_CACHE[event_key]['first_occurred'] is None:
            EVENT_CACHE[event_key]['first_occurred'] = now

        log_data["recent_count"] = EVENT_CACHE[event_key]['recent_count']
        log_data["lifetime_count"] = EVENT_CACHE[event_key]['lifetime_count']
        log_data["first_occurred"] = EVENT_CACHE[event_key]['first_occurred']
        log_data["last_occurred"] = EVENT_CACHE[event_key]['last_occurred']

        # ─── JSON File Rewrite ─────────────────────────────────────
        with open(self.file_path, 'r+', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

            f.seek(0)
            f.truncate()

            updated = False
            for entry in logs:
                if entry["event"] == log_data["event"] and entry["source"] == log_data["source"]:
                    entry["recent_count"] = log_data["recent_count"]
                    entry["last_occurred"] = log_data["last_occurred"]
                    entry["lifetime_count"] += 1
                    updated = True
                    break

            if not updated:
                log_data["lifetime_count"] = 1
                log_data["first_occurred"] = log_data["last_occurred"]
                logs.append(log_data)

            json.dump(logs, f, indent=2)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        source = record.name
        event = record.msg.split('|')[0].strip()
        message = record.msg.split('|', 1)[-1].strip() if '|' in record.msg else record.msg

        event_id = hashlib.md5(f"{source}:{event}".encode()).hexdigest()
        event_key = event_id
        now = pydatetime.datetime.now().isoformat()
        EVENT_CACHE[event_key]['recent_count'] += 1
        EVENT_CACHE[event_key]['lifetime_count'] += 1
        EVENT_CACHE[event_key]['last_occurred'] = now
        if EVENT_CACHE[event_key]['first_occurred'] is None:
            EVENT_CACHE[event_key]['first_occurred'] = now

        log_data = {
            'event': event,
            'event_id': event_id,
            'message': message,
            'recent_count': EVENT_CACHE[event_key]['recent_count'],
            'lifetime_count': EVENT_CACHE[event_key]['lifetime_count'],
            'first_occurred': EVENT_CACHE[event_key]['first_occurred'],
            'last_occurred': EVENT_CACHE[event_key]['last_occurred'],
            'level': record.levelname,
            'source': source
        }

        # Bonus trace markers
        if record.levelname in ('WARNING', 'ERROR'):
            if record.exc_info:
                tb_list = traceback.extract_tb(record.exc_info[2])  # Structured trace list
                error_type = type(record.exc_info[1]).__name__
                error_message = str(record.exc_info[1])  # Actual exception details

                tb_frames = []
                for frame in tb_list:
                    file_path = frame.filename
                    tb_frames.append({
                        "file": os.path.basename(file_path),
                        "directory": os.path.basename(os.path.dirname(file_path)),  # Only last folder
                        "line": frame.lineno,
                        "function": frame.name,
                        "code_line": frame.line,
                        "exception_message": error_message
                    })

                log_data["traceback"] = {
                    "error_type": error_type,
                    "frames": tb_frames
                }
            else:
                log_data["traceback"] = {
                    "error_type": None,
                    "frames": []
                }

        # Critical error tagging
        if record.levelname == 'ERROR':
            log_data["crash_severity"] = "critical"
            log_data["attention_required"] = True

        return json.dumps(log_data)

def get_logger(name: str) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    for level in LOG_LEVELS:
        handler = JSONLogHandler(name, level)
        handler.setLevel(getattr(logging, level))
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    _loggers[name] = logger
    return logger

def terminal_alert(message: str, level: str = "INFO"):
    color = {
        "ACTIVATED": Fore.LIGHTGREEN_EX,
        "INFO": Fore.LIGHTCYAN_EX,
        "DEBUG": Fore.LIGHTYELLOW_EX,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.LIGHTMAGENTA_EX,
        "BOOTING": Fore.LIGHTBLUE_EX
    }.get(level.upper(), Fore.LIGHTBLUE_EX)

    print(f"{color}[{level.upper()}] {message}{Style.RESET_ALL}")

DIAGNOSTICS_READY = False

def initialize_diagnostics():
    global DIAGNOSTICS_READY
    try:
        terminal_alert("[>] Diagnostics initialized...", level="INFO")
        terminal_alert(f"[>] DIAGNOSTICS using Python from: {sys.executable}", level="INFO")
        DIAGNOSTICS_READY = True
        terminal_alert(f"[+] DIAGNOSTICS_READY set to: {DIAGNOSTICS_READY}", level="INFO")
        return True
    except Exception as e:
        DIAGNOSTICS_READY = False
        raise e
