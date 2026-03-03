# ============================================================
# Supabase Client — 작업 큐 RPC 통신
# ============================================================
# requests 기반 REST RPC 호출
# POST {SUPABASE_URL}/rest/v1/rpc/{function_name}
# RPC 시그니처 고정:
#   claim_task(p_vm_id uuid) -> setof post_tasks
#   finish_task(p_vm_name text, p_task_id uuid, p_result_url text) -> void
#   fail_task(p_vm_name text, p_task_id uuid, p_error text, p_last_step text) -> void
#   heartbeat_vm(p_vm_id uuid, p_vm_name text) -> void
#   heartbeat_task(p_task_id uuid, p_vm_id uuid, p_extend_seconds int, p_vm_name text) -> void
#   requeue_stuck_tasks(p_timeout_seconds int) -> int
# ============================================================

import os
import sys

try:
    import requests
except ImportError:
    requests = None

# coupang_bot 루트 path 추가 (posting_logic 등에서 main import 시)
_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from .settings import settings

RPC_TIMEOUT = 15


def _rpc(function_name: str, payload: dict, log=None, debug=False):
    """
    Supabase REST RPC 호출
    Returns: (success: bool, data: dict|list|int|None, error_msg: str)
    """
    _log = log or print
    if not requests:
        _log("[Supabase] requests 패키지 없음. pip install requests")
        return False, None, "requests not installed"
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        _log("[Supabase] SUPABASE_URL 또는 SUPABASE_ANON_KEY 미설정")
        return False, None, "missing config"

    url = f"{settings.SUPABASE_URL}/rest/v1/rpc/{function_name}"
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }
    try:
        if debug:
            _log(f"[Supabase] RPC {function_name} start payload={payload}")
        r = requests.post(url, json=payload, headers=headers, timeout=RPC_TIMEOUT)
        if debug:
            _log(f"[Supabase] RPC {function_name} end status={r.status_code}")
        else:
            _log(f"[Supabase] RPC {function_name} → {r.status_code}")
        if r.status_code >= 400:
            err_text = r.text if r.text else ""
            _log(f"[Supabase] RPC {function_name} 실패 status={r.status_code} response={err_text[:300]}")
            return False, None, err_text
        data = r.json() if r.text else None
        return True, data, ""
    except requests.exceptions.RequestException as e:
        _log(f"[Supabase] RPC {function_name} 네트워크 오류: {e}")
        return False, None, str(e)
    except Exception as e:
        _log(f"[Supabase] RPC {function_name} 예외: {e}")
        return False, None, str(e)


def heartbeat_vm(vm_id: str, vm_name: str, log=None) -> bool:
    """워커 생존 신호 (p_vm_id uuid, p_vm_name text)"""
    _log = log or print
    ok, _, err = _rpc(
        "heartbeat_vm",
        {"p_vm_id": vm_id, "p_vm_name": vm_name or ""},
        log=_log,
    )
    if not ok:
        _log(f"[Supabase] heartbeat_vm 실패: {err[:200]}")
        return False
    return True


def heartbeat_task(task_id, vm_id: str, extend_seconds: int, vm_name: str, log=None) -> bool:
    """작업 lease 연장 (p_task_id uuid, p_vm_id uuid, p_extend_seconds int, p_vm_name text)"""
    _log = log or print
    ok, _, err = _rpc(
        "heartbeat_task",
        {
            "p_task_id": task_id,
            "p_vm_id": vm_id,
            "p_extend_seconds": int(extend_seconds),
            "p_vm_name": vm_name or "",
        },
        log=_log,
    )
    if not ok:
        _log(f"[Supabase] heartbeat_task 실패: {err[:200]}")
        return False
    return True


def claim_task(vm_id: str, log=None):
    """
    pending → assigned 원자적 선점 (p_vm_id uuid)
    Returns: task dict 또는 None
    """
    _log = log or print
    ok, data, err = _rpc("claim_task", {"p_vm_id": vm_id}, log=_log)
    if not ok:
        _log(f"[Supabase] claim_task 실패: {err[:200]}")
        return None
    if data is None:
        return None
    if isinstance(data, dict):
        return data if data else None
    if isinstance(data, list):
        return data[0] if data else None
    return None


def finish_task(vm_name: str, task_id, result_url: str, log=None) -> bool:
    """작업 완료 처리 (p_vm_name text, p_task_id uuid, p_result_url text) — assigned_vm_name으로 매칭"""
    _log = log or print
    payload = {
        "p_vm_name": vm_name or "",
        "p_task_id": task_id,
        "p_result_url": result_url or "",
    }
    ok, _, err = _rpc("finish_task", payload, log=_log)
    if not ok:
        _log(f"[Supabase] finish_task 실패: {err[:200]}")
        return False
    return True


def fail_task(vm_name: str, task_id, error_message: str, last_step: str = "", log=None) -> bool:
    """작업 실패 처리 (p_vm_name text, p_task_id uuid, p_error text, p_last_step text) — assigned_vm_name으로 매칭"""
    _log = log or print
    ok, _, err = _rpc(
        "fail_task",
        {
            "p_vm_name": vm_name or "",
            "p_task_id": task_id,
            "p_error": error_message or "",
            "p_last_step": last_step or "",
        },
        log=_log,
    )
    if not ok:
        _log(f"[Supabase] fail_task 실패: {err[:200]}")
        return False
    return True


def requeue_stuck_tasks(timeout_sec: int, log=None):
    """
    stuck task 복구 (p_timeout_seconds int)
    Returns: (ok, data, err)
    """
    payload = {"p_timeout_seconds": int(timeout_sec)}
    ok, data, err = _rpc("requeue_stuck_tasks", payload, log=log)
    if not ok and log:
        log(f"[Supabase] requeue_stuck_tasks 실패: {err}")
    return ok, data, err
