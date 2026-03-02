# ============================================================
# Cafe Autojoin Handler — post_tasks channel='cafe_autojoin'
# ============================================================
# task.meta (또는 task)에서 payload 추출 후 run_cafe_join_job 호출
# ============================================================

import sys
import os

# 부모 프로젝트 경로 추가 (cafe_autojoin, supabase_client 등)
_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)


def run(task: dict, log=None) -> dict:
    """
    channel='cafe_autojoin' 작업 처리.
    task.meta 또는 task에서 payload 추출:
      owner_user_id, program_username, naver_id, naver_pw,
      captcha_api_key, accounts, immediate
    Returns: {"ok": True, "result_url": "..."} or {"ok": False, "error": "...", "last_step": "..."}
    """
    _log = log or print
    meta = task.get("meta") or task
    if not isinstance(meta, dict):
        meta = {}

    owner_user_id = meta.get("owner_user_id") or task.get("user_id")
    program_username = (meta.get("program_username") or "").strip()
    naver_id = (meta.get("naver_id") or "").strip()
    naver_pw = (meta.get("naver_pw") or "").strip()
    captcha_api_key = (meta.get("captcha_api_key") or "").strip() or None
    accounts = meta.get("accounts")
    immediate = bool(meta.get("immediate", False))

    if not program_username:
        return {"ok": False, "error": "program_username required", "last_step": "init"}
    if not naver_id or not naver_pw:
        if not (accounts and len(accounts) > 0):
            return {"ok": False, "error": "naver_id/naver_pw or accounts required", "last_step": "init"}

    try:
        vm_name = None
        try:
            from .vm_identity import get_vm_name
            vm_name = get_vm_name()
        except Exception:
            pass
        from cafe_autojoin import run_cafe_join_job
        ok = run_cafe_join_job(
            owner_user_id=owner_user_id,
            program_username=program_username,
            naver_id=naver_id,
            naver_pw=naver_pw,
            captcha_api_key=captcha_api_key,
            stop_flag=lambda: False,
            log=_log,
            on_progress=None,
            immediate=immediate,
            accounts=accounts,
            vm_name=vm_name,
        )
        if ok:
            return {"ok": True, "result_url": f"cafe_autojoin_done:{program_username}"}
        return {"ok": False, "error": "run_cafe_join_job returned False", "last_step": "execute"}
    except Exception as e:
        _log(f"[cafe_autojoin] error: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": str(e), "last_step": "execute"}
