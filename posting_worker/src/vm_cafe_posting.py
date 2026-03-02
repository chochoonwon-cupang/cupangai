# ============================================================
# VM 카페 포스팅 — 네이버 아이디별 50개 유지, 10일 경과 삭제, 실패 삭제
# ============================================================
# run_default_job에서 호출: task 없을 때 VM 네이버 계정별 카페 가입+글작성
# ============================================================

import os
import sys
import random
from datetime import datetime, timezone

_PARENT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

# 기본값 (cafe_join_policy에서 오버라이드)
CAFE_TARGET_COUNT = 50
EXPIRE_DAYS = 10


def _get_gemini_key(log=None):
    _log = log or (lambda m: None)
    try:
        from shared.gui_data import get_admin_settings
        settings = get_admin_settings(log=_log)
        return (settings or {}).get("gemini_api_key") or (settings or {}).get("gemini_key") or ""
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def _get_coupang_keys(username=None, log=None):
    _log = log or (lambda m: None)
    un = username or os.environ.get("COMM_USERNAME", "").strip()
    if not un:
        return None, None
    try:
        from supabase_client import fetch_user_coupang_keys
        keys = fetch_user_coupang_keys(un, log=_log)
        if keys and len(keys) >= 2:
            return keys[0], keys[1]
    except Exception as e:
        _log(f"[VM] fetch_user_coupang_keys 실패: {e}")
    return None, None


def _get_keyword(log=None):
    _log = log or (lambda m: None)
    try:
        from shared.gui_data import get_admin_keywords
        kws = get_admin_keywords(count=1, log=_log)
        if kws and len(kws) > 0:
            return random.choice(kws)
    except Exception:
        pass
    return "건강식품"


def run_one_account(naver_id: str, naver_pw: str, vm_name: str, log=None):
    """
    단일 네이버 계정에 대해:
    1) 10일 경과 카페 삭제
    2) 카페 수 < 50이면 run_cafe_join_job 실행
    3) 카페 리스트로 1건 포스팅
    4) 성공 시 last_posted_at 갱신, 실패 시 해당 카페 삭제
    """
    _log = log or print
    if not naver_id or not naver_pw:
        _log(f"[VM] naver_id/pw 없음 — 스킵")
        return

    try:
        from supabase_client import (
            delete_expired_agent_cafes,
            fetch_agent_cafe_lists_full,
            update_program_cafe_list_status,
            delete_agent_cafe_list,
            fetch_cafe_join_policy,
        )
    except ImportError as e:
        _log(f"[VM] supabase_client import 실패: {e}")
        return

    policy = fetch_cafe_join_policy(log=_log) or {}
    expire_days = int(policy.get("expire_days") or EXPIRE_DAYS)
    target_count = int(policy.get("target_count") or CAFE_TARGET_COUNT)

    # 1) N일 경과 카페 삭제 (cafe_join_policy.expire_days)
    deleted = delete_expired_agent_cafes(naver_id, days=expire_days, log=_log)
    if deleted > 0:
        _log(f"[VM] {naver_id} {expire_days}일 경과 {deleted}건 삭제")

    # 2) 카페 수 확인, < target_count이면 1개 가입 후 해당 카페에 글작성
    cafes = fetch_agent_cafe_lists_full(naver_id, log=_log)
    count = len(cafes)
    if count < target_count:
        _log(f"[VM] {naver_id} 카페 {count}개 (목표 {target_count}) → 1개 가입 후 글작성")
        try:
            from cafe_autojoin import run_cafe_join_job
            from config import OWNER_USER_ID
            ok = run_cafe_join_job(
                owner_user_id=OWNER_USER_ID,
                program_username=naver_id,
                naver_id=naver_id,
                naver_pw=naver_pw,
                stop_flag=lambda: False,
                log=_log,
                immediate=True,
                vm_name=vm_name,
                target_count_override=1,
            )
            if ok:
                cafes = fetch_agent_cafe_lists_full(naver_id, log=_log)
                count = len(cafes)
                _log(f"[VM] {naver_id} 카페 가입 후 {count}개")
        except Exception as e:
            _log(f"[VM] run_cafe_join_job 실패: {e}")

    if not cafes:
        _log(f"[VM] {naver_id} 카페 리스트 비어있음 — 스킵")
        return

    # 3) 포스팅 1건 (last_posted_at 오래된 순 또는 랜덤)
    cafes_sorted = sorted(cafes, key=lambda c: (c.get("last_posted_at") or "1970-01-01"))
    cafe = cafes_sorted[0]
    cafe_url = cafe.get("cafe_url", "")
    cafe_id = cafe.get("cafe_id", "")
    menu_id = cafe.get("menu_id", "")

    gemini_key = _get_gemini_key(log=_log)
    coupang_ak, coupang_sk = _get_coupang_keys(naver_id, log=_log)
    if not coupang_ak or not coupang_sk:
        coupang_ak, coupang_sk = _get_coupang_keys(log=_log)
    if not coupang_ak or not coupang_sk:
        _log(f"[VM] {naver_id} 쿠팡 API 키 없음 (COMM_USERNAME 또는 users 테이블) — 스킵")
        return

    keyword = _get_keyword(log=_log)

    try:
        from cafe_poster import setup_driver, login_to_naver, safe_quit_driver
        from main import run_pipeline
        from cafe_poster import write_cafe_post, write_comment
        from supabase_client import fetch_banned_brands, is_keyword_banned, insert_post_log
    except ImportError as e:
        _log(f"[VM] import 실패: {e}")
        return

    driver = None
    try:
        driver = setup_driver(headless=True)
        if not login_to_naver(driver, naver_id, naver_pw, log=_log):
            _log(f"[VM] {naver_id} 네이버 로그인 실패")
            return

        banned = []
        try:
            banned = fetch_banned_brands(log=_log)
        except Exception:
            pass
        if is_keyword_banned(keyword, banned):
            _log(f"[VM] 키워드 '{keyword}' 활동금지 — 스킵")
            return

        result = run_pipeline(
            keyword, limit=5, gemini_api_key=gemini_key or None,
            log_callback=_log, coupang_access_key=coupang_ak, coupang_secret_key=coupang_sk,
            use_product_name=False, category="건강식품",
        )
        if not result or not result.get("post_content"):
            _log(f"[VM] {naver_id} 파이프라인 결과 없음")
            return

        post_content = result.get("post_content", "")
        image_paths = result.get("image_paths", {})
        products = result.get("products", [])

        from cafe_poster import _split_title_body, _strip_part_markers
        title, body = _split_title_body(post_content)
        title = _strip_part_markers(title)
        body = _strip_part_markers(body)

        ordered_images = []
        for p in (products or []):
            pname = p.get("productName", "")
            img = image_paths.get(pname, "")
            if img and os.path.isfile(img):
                ordered_images.append(img)

        wr = write_cafe_post(driver, cafe_id, menu_id, title, body, image_map=ordered_images, keyword=keyword, log=_log)
        ok = wr[0] if isinstance(wr, (tuple, list)) else bool(wr)
        fail_reason = wr[1] if isinstance(wr, (tuple, list)) and len(wr) > 1 else None
        if ok:
            write_comment(driver, products or [], log=_log)
            now_iso = datetime.now(timezone.utc).isoformat()
            update_program_cafe_list_status(cafe_url, naver_id=naver_id, last_posted_at=now_iso, log=_log)
            _log(f"[VM] {naver_id} 포스팅 성공 — last_posted_at 갱신")
            try:
                insert_post_log(program_username=naver_id, keyword=keyword, posting_url=driver.current_url if driver else None, server_name=vm_name or "vm", log=_log)
            except Exception:
                pass
        elif fail_reason in ("member_required", "button_not_found"):
            delete_agent_cafe_list(cafe_url, naver_id=naver_id, log=_log)
            _log(f"[VM] {naver_id} 포스팅 실패 — 카페 리스트에서 삭제")

        for img in ordered_images:
            try:
                if os.path.isfile(img):
                    os.remove(img)
            except Exception:
                pass

    except Exception as e:
        _log(f"[VM] {naver_id} 포스팅 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                safe_quit_driver(driver)
            except Exception:
                pass


def run_vm_cafe_cycle(vm_name: str, accounts: list, log=None):
    """VM 네이버 계정별로 run_one_account 실행."""
    _log = log or print
    if not accounts or len(accounts) == 0:
        _log("[VM] 네이버 계정 없음 — vm_accounts 확인")
        return
    for acc in accounts:
        nid = (acc.get("id") or "").strip()
        npw = (acc.get("pw") or "").strip()
        if nid and npw:
            run_one_account(nid, npw, vm_name, log=_log)
