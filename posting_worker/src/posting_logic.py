# ============================================================
# Posting Logic — 포스팅 실행 진입점
# ============================================================
# run(task) 단일 진입점
# 반환: {"ok": True, "result_url": "..."} or {"ok": False, "error": "...", "last_step": "..."}
# channel/platform별 분기: cafe_autojoin → cafe_autojoin_handler
# ============================================================

import random
import time


def _get_keyword_from_task(task: dict) -> str:
    """1) task.keyword 최우선, 2) payload['keyword'] 호환, 3) payload['keywords'][0] 호환"""
    kw = (task.get("keyword") or "").strip()
    if kw:
        return kw
    payload = task.get("payload") or task.get("meta") or {}
    kw2 = (payload.get("keyword") or "").strip()
    if kw2:
        return kw2
    kws = payload.get("keywords")
    if kws and len(kws) > 0:
        return str(kws[0]).strip()
    return ""


def run(task: dict) -> dict:
    """
    작업 1건을 처리합니다.
    task: {"id", "platform", "channel", "keyword", "payload", "meta", ...}
    Returns: {"ok": True, "result_url": "..."} or {"ok": False, "error": "..."}
    """
    task_id = task.get("id")
    if task_id is None:
        return {"ok": False, "error": "task id is None", "last_step": "init"}

    channel = task.get("channel") or task.get("platform", "cafe")

    # channel='cafe_autojoin' → 전용 핸들러
    if channel == "cafe_autojoin":
        from . import cafe_autojoin_handler
        return cafe_autojoin_handler.run(task)

    # blog / cafe (기본): task.keyword 최우선, payload 호환
    keyword = _get_keyword_from_task(task)
    current_step = "init"
    try:
        current_step = "posting"
        sleep_sec = random.uniform(2, 5)
        time.sleep(sleep_sec)
        result_url = f"https://example.com/test/{task_id}"
        return {"ok": True, "result_url": result_url}
    except Exception as e:
        return {"ok": False, "error": str(e), "last_step": current_step}
