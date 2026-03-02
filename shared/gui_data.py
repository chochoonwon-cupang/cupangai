# ============================================================
# GUI용 Supabase 데이터 — shared/sb.py 기반 (유일한 Supabase 접근 경로)
# ============================================================
# gui.py는 이 모듈만 import. supabase_client 직접 호출 금지.
# ============================================================

import datetime
import random
from shared.sb import get_client, select

VALID_CATEGORIES = ("건강식품", "생활용품", "가전제품", "유아/출산", "기타")


# ─────────────────────────────────────────────────────────────
# 앱 링크 / 배너 / 도우미 카페
# ─────────────────────────────────────────────────────────────

def fetch_app_links(log=None):
    """app_links 테이블: link_key → url/value 매핑 (url 또는 value 컬럼 지원)"""
    _log = log or (lambda m: None)
    try:
        rows = select("app_links", columns="*", log=_log)
        links = {}
        for row in rows or []:
            k = (row.get("link_key") or "").strip()
            v = (row.get("url") or row.get("value") or "").strip()
            if k and v:
                links[k] = v
        if links:
            _log(f"[Supabase] 앱 링크 {len(links)}개 로드")
        return links
    except Exception as e:
        _log(f"[Supabase] app_links 조회 실패: {e}")
        return {}


def fetch_banners(log=None):
    """banners 테이블: [{main_text, sub_text, url}, ...]"""
    _log = log or (lambda m: None)
    try:
        rows = select("banners", columns="main_text, sub_text, url", log=_log)
        banners = []
        for row in rows:
            mt = (row.get("main_text") or "").strip()
            st = (row.get("sub_text") or "").strip()
            url = (row.get("url") or "").strip()
            if mt and url:
                banners.append({"main_text": mt, "sub_text": st, "url": url})
        if banners:
            _log(f"[Supabase] 배너 {len(banners)}개 로드")
        return banners
    except Exception as e:
        _log(f"[Supabase] banners 조회 실패: {e}")
        return []


def fetch_program_cafe_lists(program_username=None, naver_id=None, statuses=None, log=None, use_service=False):
    """agent_cafe_lists에서 카페 리스트 조회. naver_id 우선, 없으면 program_username (도우미 '모두사용' 시)"""
    _log = log or (lambda m: None)
    statuses = statuses or ["saved", "joined"]
    try:
        client = get_client(use_service_role=use_service)
        q = client.table("agent_cafe_lists").select("cafe_url, cafe_id, menu_id").in_("status", statuses).order("created_at")
        if naver_id and str(naver_id).strip():
            q = q.eq("naver_id", str(naver_id).strip())
        elif program_username and str(program_username).strip():
            q = q.eq("program_username", str(program_username).strip())
        else:
            return []
        r = q.execute()
        return [
            {"cafe_url": row.get("cafe_url"), "cafe_id": row.get("cafe_id"), "menu_id": row.get("menu_id")}
            for row in (r.data or [])
        ]
    except Exception as e:
        _log(f"[Supabase] agent_cafe_lists 조회 실패: {e}")
        return []


def fetch_helper_cafes(log=None):
    """helper_cafes 테이블: [{"cafe_url", "cafe_id", "menu_id"}, ...]"""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=False)
        r = client.table("helper_cafes").select("cafe_url, cafe_id, menu_id, created_at").order("sort_order").execute()
        cafes = []
        for row in (r.data or []):
            url = (row.get("cafe_url") or "").strip()
            cid = (row.get("cafe_id") or "").strip()
            mid = (row.get("menu_id") or "").strip()
            if url and cid and mid:
                cafes.append({"cafe_url": url, "cafe_id": cid, "menu_id": mid, "created_at": row.get("created_at")})
        if cafes:
            _log(f"[Supabase] 도우미 카페 {len(cafes)}개 로드")
        return cafes
    except Exception as e:
        _log(f"[Supabase] helper_cafes 조회 실패: {e}")
        return []


def fetch_helper_new_cafe_since(log=None):
    """app_links에서 helper_new_cafe_since (YYYY-MM-DD)"""
    _log = log or (lambda m: None)
    try:
        rows = select("app_links", filters={"link_key": "helper_new_cafe_since"}, columns="url", limit=1, log=_log)
        if rows:
            val = (rows[0].get("url") or "").strip()
            if val:
                return val
        return None
    except Exception as e:
        _log(f"[Supabase] helper_new_cafe_since 조회 실패: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# 관리자 설정 / 카페 타겟 (get_admin_settings, get_cafe_targets)
# ─────────────────────────────────────────────────────────────

def get_admin_settings(log=None):
    """app_links에서 gemini_key, captcha_key 등 (읽기 전용). 별칭 포함."""
    _log = log or (lambda m: None)
    links = fetch_app_links(log=_log)
    out = dict(links)
    if "gemini_api_key" in out:
        out["gemini_key"] = out["gemini_api_key"]
    if "captcha_api_key" in out:
        out["captcha_key"] = out["captcha_api_key"]
    return out


def get_cafe_targets(log=None):
    """helper_cafes에서 (cafe_id, menu_id, name) 리스트"""
    _log = log or (lambda m: None)
    cafes = fetch_helper_cafes(log=_log)
    out = []
    for c in cafes:
        cid = (c.get("cafe_id") or "").strip()
        mid = (c.get("menu_id") or "").strip()
        url = (c.get("cafe_url") or "").strip()
        name = cid
        if url:
            parts = url.rstrip("/").split("/")
            if parts:
                name = parts[-1] or cid
        if cid and mid:
            out.append({"cafe_id": cid, "menu_id": mid, "name": name})
    return out


# ─────────────────────────────────────────────────────────────
# 사용자 프로필 / 키워드
# ─────────────────────────────────────────────────────────────

def get_user_profile(user_id=None, username=None, log=None):
    """사용자 프로필: 쿠팡 키, 사용량, 내 키워드 사용 여부 (profiles 테이블)"""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=True)
        cols = "coupang_access_key, coupang_secret_key, distribute_keyword, distribute_category"
        r = None
        if user_id:
            try:
                r = client.table("profiles").select(cols).eq("user_id", user_id).limit(1).execute()
            except Exception:
                pass
            if not r or not r.data or len(r.data) == 0:
                try:
                    r = client.table("profiles").select(cols).eq("id", user_id).limit(1).execute()
                except Exception:
                    pass
        elif username:
            try:
                r = client.table("profiles").select(cols).eq("coupang_id", username).limit(1).execute()
            except Exception:
                pass
            if not r or not r.data or len(r.data) == 0:
                r = client.table("profiles").select(cols).eq("username", username).limit(1).execute()
            if not r or not r.data or len(r.data) == 0:
                try:
                    r = client.table("profiles").select(cols).eq("login_id", username).limit(1).execute()
                except Exception:
                    pass
        else:
            return None
        if not r or not r.data or len(r.data) == 0:
            return None
        row = r.data[0]
        ak = (row.get("coupang_access_key") or "").strip()
        sk = (row.get("coupang_secret_key") or "").strip()
        raw_kw = (row.get("distribute_keyword") or "").strip()
        return {
            "coupang_access_key": ak,
            "coupang_secret_key": sk,
            "search_limit": 5,
            "use_own_keywords": bool(raw_kw),
        }
    except Exception as e:
        _log(f"[GUI] get_user_profile 실패: {e}")
        return None


def get_user_keywords(user_id=None, username=None, log=None):
    """user_keywords 테이블 (없으면 [])"""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=True)
        q = client.table("user_keywords").select("keyword")
        if user_id:
            q = q.eq("user_id", user_id)
        elif username:
            q = q.eq("username", username)
        else:
            return []
        r = q.execute()
        return [str(row.get("keyword", "")).strip() for row in (r.data or []) if row.get("keyword")]
    except Exception:
        return []


def fetch_paid_members(log=None):
    """paid_members (active=true)"""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=False)
        r = client.table("paid_members").select("name, keywords, category, coupang_access_key, coupang_secret_key").eq("active", True).execute()
        members = []
        for row in (r.data or []):
            raw_kw = row.get("keywords", "")
            kw_list = [k.strip() for k in raw_kw.split(",") if k.strip()]
            if not kw_list:
                continue
            ak, sk = row.get("coupang_access_key", ""), row.get("coupang_secret_key", "")
            if not ak or not sk:
                continue
            raw_cat = (row.get("category") or "").strip()
            category = raw_cat if raw_cat in VALID_CATEGORIES else "기타"
            members.append({
                "name": row.get("name", "이름없음"),
                "keywords": kw_list,
                "category": category,
                "coupang_access_key": ak,
                "coupang_secret_key": sk,
            })
        if members:
            _log(f"[Supabase] 유료회원 {len(members)}명 로드 완료")
        return members
    except Exception as e:
        _log(f"[Supabase] paid_members 조회 실패: {e}")
        return []


def fetch_paid_member_keywords_pool(count=None, log=None):
    """유료회원 키워드 랜덤 풀"""
    _log = log or (lambda m: None)
    members = fetch_paid_members(log=_log)
    pool = []
    for m in members:
        for kw in (m.get("keywords") or []):
            if kw and str(kw).strip():
                pool.append(str(kw).strip())
    random.shuffle(pool)
    if not pool:
        return []
    if count and count > 0:
        return pool[:count] if len(pool) >= count else [random.choice(pool) for _ in range(count)]
    return pool


def get_admin_keywords(count=None, log=None):
    """admin_keywords 또는 paid_members fallback"""
    _log = log or (lambda m: None)
    try:
        rows = select("admin_keywords", columns="keyword", log=_log)
        if rows:
            pool = [str(r.get("keyword", "")).strip() for r in rows if r.get("keyword")]
            if pool:
                random.shuffle(pool)
                if count and count > 0:
                    return pool[:count] if len(pool) >= count else [random.choice(pool) for _ in range(count)]
                return pool
    except Exception:
        pass
    return fetch_paid_member_keywords_pool(count=count, log=_log)


def get_user_keywords_or_fallback(user_id=None, username=None, count=None, log=None):
    """유저 키워드 있으면 사용, 없으면 admin/paid fallback"""
    kw = get_user_keywords(user_id=user_id, username=username, log=log)
    if kw and len(kw) >= 1:
        return kw
    return get_admin_keywords(count=count, log=log)


# ─────────────────────────────────────────────────────────────
# 추천인 / 쿠팡 키 / 금지 브랜드
# ─────────────────────────────────────────────────────────────

def fetch_referrer(referrer_username: str, log=None):
    """users 테이블에서 추천인 정보"""
    _log = log or (lambda m: None)
    if not (referrer_username or "").strip():
        return None
    referrer_username = referrer_username.strip()
    try:
        client = get_client(use_service_role=True)
        r = client.table("users").select("username, distribute_keyword, distribute_category, coupang_access_key, coupang_secret_key").eq("username", referrer_username).limit(1).execute()
        if not r.data or len(r.data) == 0:
            return None
        row = r.data[0]
        raw_kw = (row.get("distribute_keyword") or "").strip()
        kw_list = [k.strip() for k in raw_kw.split(",") if k.strip()]
        if not kw_list:
            return None
        ak = (row.get("coupang_access_key") or "").strip()
        sk = (row.get("coupang_secret_key") or "").strip()
        if not ak or not sk:
            return None
        raw_cat = (row.get("distribute_category") or "").strip()
        category = raw_cat if raw_cat in VALID_CATEGORIES else "기타"
        return {
            "name": referrer_username,
            "keywords": kw_list,
            "category": category,
            "coupang_access_key": ak,
            "coupang_secret_key": sk,
        }
    except Exception as e:
        _log(f"[Supabase] 추천인 조회 실패: {e}")
        return None


def fetch_user_coupang_keys(username: str = None, user_id: str = None, log=None):
    """profiles 테이블에서 쿠팡 API 키 (SaaS 대시보드에서 저장한 값).
    username 또는 user_id로 조회. user_id 우선 (profiles.id 또는 profiles.user_id = auth.users.id)."""
    _log = log or (lambda m: None)
    if not (username or "").strip() and not (user_id or "").strip():
        return None
    try:
        client = get_client(use_service_role=True)
        r = None
        uid = str(user_id or "").strip()
        if uid:
            try:
                r = client.table("profiles").select("coupang_access_key, coupang_secret_key").eq("user_id", uid).limit(1).execute()
            except Exception:
                pass
            if not r or not r.data or len(r.data) == 0:
                try:
                    r = client.table("profiles").select("coupang_access_key, coupang_secret_key").eq("id", uid).limit(1).execute()
                except Exception:
                    pass
        un = str(username or "").strip()
        if un and (not r or not r.data or len(r.data) == 0):
            try:
                r = client.table("profiles").select("coupang_access_key, coupang_secret_key").eq("coupang_id", un).limit(1).execute()
            except Exception:
                pass
            if not r or not r.data or len(r.data) == 0:
                r = client.table("profiles").select("coupang_access_key, coupang_secret_key").eq("username", un).limit(1).execute()
            if not r or not r.data or len(r.data) == 0:
                try:
                    r = client.table("profiles").select("coupang_access_key, coupang_secret_key").eq("login_id", un).limit(1).execute()
                except Exception:
                    pass
        if not r or not r.data or len(r.data) == 0:
            return None
        row = r.data[0]
        ak = (row.get("coupang_access_key") or "").strip()
        sk = (row.get("coupang_secret_key") or "").strip()
        if not ak or not sk:
            return None
        return (ak, sk)
    except Exception as e:
        _log(f"[Supabase] profiles 쿠팡키 조회 실패: {e}")
        return None


def fetch_banned_brands(log=None):
    """banned_brands 테이블"""
    _log = log or (lambda m: None)
    try:
        rows = select("banned_brands", columns="brand_name", log=_log)
        brands = [r.get("brand_name", "").strip() for r in rows if r.get("brand_name", "").strip()]
        if brands:
            _log(f"[Supabase] 활동금지 브랜드 {len(brands)}개 로드")
        return brands
    except Exception as e:
        _log(f"[Supabase] banned_brands 조회 실패: {e}")
        return []


def is_keyword_banned(keyword: str, banned_brands: list) -> bool:
    """키워드에 금지 브랜드 포함 여부"""
    if not keyword or not banned_brands:
        return False
    kw_lower = keyword.lower()
    return any(b.strip().lower() in kw_lower for b in banned_brands if b and b.strip())


# ─────────────────────────────────────────────────────────────
# post_tasks / enqueue_post_tasks (단일 실행 플로우)
# ─────────────────────────────────────────────────────────────

def get_cost_per_post(user_id, log=None):
    """profiles.cost_per_post 반환, 없으면 0"""
    _log = log or (lambda m: None)
    if not user_id:
        return 0
    try:
        client = get_client(use_service_role=True)
        r = client.table("profiles").select("cost_per_post").eq("id", user_id).limit(1).execute()
        if r.data and len(r.data) > 0:
            val = r.data[0].get("cost_per_post")
            if val is not None:
                return int(val)
    except Exception as e:
        _log(f"[GUI] get_cost_per_post 실패: {e}")
    return 0


def enqueue_post_tasks_paid(user_id, channel, count, cost=None, payload=None, log=None):
    """
    post_tasks 테이블에 pending 작업 생성 (유료 RPC)
    cost 미지정 시 profiles.cost_per_post 사용
    Args:
        user_id: 사용자 UUID
        channel: 'blog' | 'cafe'
        count: 생성할 작업 수
        cost: 비용 (None이면 profiles.cost_per_post)
        payload: 추가 payload (jsonb)
    Returns:
        (ok: bool, data, err: str)
    """
    _log = log or (lambda m: None)
    from shared.sb import rpc
    if cost is None:
        cost = get_cost_per_post(user_id, log=_log)
    rpc_payload = {
        "p_user_id": str(user_id) if user_id else "",
        "p_channel": str(channel or "cafe").lower(),
        "p_count": int(count) if count else 1,
        "p_cost": int(cost) if cost is not None else 0,
        "p_payload": payload if isinstance(payload, dict) else {},
    }
    ok, data, err = rpc("enqueue_post_tasks_paid", rpc_payload, use_service_role=True, log=_log)
    return ok, data, err


def fetch_pending_post_tasks(user_id=None, limit=1, log=None):
    """post_tasks에서 pending 작업 조회 (created_at 오름차순).
    user_id가 있으면 해당 사용자 작업만, 없으면 전체 pending 작업 조회."""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=True)
        q = (
            client.table("post_tasks")
            .select("id, user_id, keyword, channel, payload")
            .eq("status", "pending")
            .order("created_at", desc=False)
            .limit(limit)
        )
        if user_id and str(user_id).strip():
            q = q.eq("user_id", str(user_id))
        r = q.execute()
        return list(r.data or [])
    except Exception as e:
        _log(f"[GUI] fetch_pending_post_tasks 실패: {e}")
        return []


def claim_post_task_for_gui(task_id, user_id, vm_name=None, log=None):
    """post_tasks 1건을 선점 (status → assigned, assigned_vm_name 저장). 원자적 업데이트로 중복 선점 방지."""
    _log = log or (lambda m: None)
    if not task_id:
        return False
    try:
        client = get_client(use_service_role=True)
        data = {"status": "assigned"}
        if vm_name and str(vm_name).strip():
            data["assigned_vm_name"] = str(vm_name).strip()
        q = client.table("post_tasks").update(data).eq("id", task_id).eq("status", "pending")
        if user_id is not None and str(user_id).strip() != "":
            q = q.eq("user_id", str(user_id))
        r = q.execute()
        return bool(r.data and len(r.data) > 0)
    except Exception as e:
        _log(f"[GUI] claim_post_task_for_gui 실패: {e}")
        return False


def finish_post_task_for_gui(task_id, user_id, success=True, published_url=None, log=None):
    """post_tasks 1건 완료 처리 (status → done/failed, published_url 저장)"""
    _log = log or (lambda m: None)
    if not task_id:
        return False
    status = "done" if success else "failed"
    try:
        client = get_client(use_service_role=True)
        data = {"status": status, "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if published_url and str(published_url).strip():
            data["published_url"] = str(published_url).strip()
        q = client.table("post_tasks").update(data).eq("id", task_id)
        if user_id is not None and str(user_id).strip() != "":
            q = q.eq("user_id", str(user_id))
        q.execute()
        return True
    except Exception as e:
        _log(f"[GUI] finish_post_task_for_gui 실패: {e}")
        return False


def fetch_cafe_join_policy(log=None):
    """cafe_join_policy id=1 (service_role)"""
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=True)
        r = client.table("cafe_join_policy").select("*").eq("id", 1).limit(1).execute()
        rows = r.data or []
        if rows:
            row = rows[0]
            year_min = row.get("created_year_min") or row.get("min_created_year")
            year_max = row.get("created_year_max") or row.get("max_created_year")
            recent_en = row.get("recent_post_enabled")
            if recent_en is None:
                rnrp = row.get("require_no_recent_posts")
                recent_en = True if rnrp is None else bool(rnrp)
            return {
                "run_days": row.get("run_days") or [4, 14, 24],
                "start_time": (row.get("start_time") or "09:00").strip() or "09:00",
                "created_year_min": int(year_min or 2020),
                "created_year_max": int(year_max or 2025),
                "recent_post_days": int(row.get("recent_post_days") or 7),
                "recent_post_enabled": bool(recent_en),
                "target_count": int(row.get("target_count") or 50),
                "expire_days": int(row.get("expire_days") or 10),
                "search_keyword": (row.get("search_keyword") or "").strip(),
            }
    except Exception as e:
        _log(f"[Supabase] cafe_join_policy 조회 실패: {e}")
    return {"run_days": [4, 14, 24], "start_time": "09:00", "created_year_min": 2020, "created_year_max": 2025, "recent_post_days": 7, "recent_post_enabled": True, "target_count": 50, "expire_days": 10, "search_keyword": ""}
