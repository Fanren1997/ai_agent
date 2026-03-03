from __future__ import annotations

import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SYNC_SCRIPT = PROJECT_ROOT / "data_sync" / "access_mysql_sync_tool.py"

_SYNC_LOCK = threading.Lock()
_SYNC_PROCESS: Optional[subprocess.Popen[str]] = None
_SYNC_OUTPUT: Deque[str] = deque(maxlen=200)
_SYNC_STATE: Dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "ended_at": None,
    "exit_code": None,
    "error": None,
    "pid": None,
}


def _now() -> float:
    return time.time()


def _fmt_time(ts: Optional[float]) -> Optional[str]:
    if not ts:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _append_output(line: str) -> None:
    clean = line.rstrip("\n")
    if clean:
        _SYNC_OUTPUT.append(clean)


def _update_state(**kwargs: Any) -> None:
    _SYNC_STATE.update(kwargs)


def _monitor_process(process: subprocess.Popen[str], stream_output: bool) -> None:
    global _SYNC_PROCESS
    try:
        if process.stdout:
            for line in process.stdout:
                _append_output(line)
                if stream_output:
                    print(line.rstrip("\n"))
        exit_code = process.wait()
    except Exception as exc:
        with _SYNC_LOCK:
            if _SYNC_PROCESS is process:
                _update_state(
                    status="failed",
                    ended_at=_now(),
                    exit_code=getattr(process, "returncode", None),
                    error=str(exc),
                )
                _SYNC_PROCESS = None
        return

    with _SYNC_LOCK:
        if _SYNC_PROCESS is process:
            _update_state(
                status="success" if exit_code == 0 else "failed",
                ended_at=_now(),
                exit_code=exit_code,
            )
            _SYNC_PROCESS = None


def start_sync(stream_output: bool = False) -> Dict[str, Any]:
    """Start sync in background if not already running."""
    global _SYNC_PROCESS
    if not SYNC_SCRIPT.exists():
        with _SYNC_LOCK:
            _update_state(status="error", error=f"sync script not found: {SYNC_SCRIPT}")
        return {"ok": False, "status": "error", "message": f"未找到同步脚本: {SYNC_SCRIPT}"}

    with _SYNC_LOCK:
        if _SYNC_PROCESS and _SYNC_PROCESS.poll() is None:
            return {
                "ok": False,
                "status": "running",
                "message": "同步任务正在运行",
                "pid": _SYNC_STATE.get("pid"),
                "started_at": _fmt_time(_SYNC_STATE.get("started_at")),
            }

        try:
            process = subprocess.Popen(
                [sys.executable, str(SYNC_SCRIPT)],
                cwd=str(SYNC_SCRIPT.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        except Exception as exc:
            _update_state(status="error", error=str(exc), ended_at=_now())
            return {"ok": False, "status": "error", "message": f"启动同步失败: {exc}"}

        _SYNC_OUTPUT.clear()
        _SYNC_PROCESS = process
        _update_state(
            status="running",
            started_at=_now(),
            ended_at=None,
            exit_code=None,
            error=None,
            pid=process.pid,
        )

    threading.Thread(target=_monitor_process, args=(process, stream_output), daemon=True).start()
    return {"ok": True, "status": "running", "message": "同步任务已启动", "pid": process.pid}


def get_status() -> Dict[str, Any]:
    with _SYNC_LOCK:
        running = _SYNC_PROCESS is not None and _SYNC_PROCESS.poll() is None
        status = "running" if running else _SYNC_STATE.get("status", "idle")
        output_tail = list(_SYNC_OUTPUT)[-20:]
        return {
            "status": status,
            "running": running,
            "started_at": _fmt_time(_SYNC_STATE.get("started_at")),
            "ended_at": _fmt_time(_SYNC_STATE.get("ended_at")),
            "exit_code": _SYNC_STATE.get("exit_code"),
            "error": _SYNC_STATE.get("error"),
            "pid": _SYNC_STATE.get("pid"),
            "output": output_tail,
        }
