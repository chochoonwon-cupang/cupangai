# ============================================================
# Supabase 클라이언트 — 유료회원 데이터 관리
# ============================================================
# configs/app_config.json 기반 — shared.sb 사용
# ============================================================

import datetime

from config import OWNER_USER_ID
from shared.sb import get_client

# 유효한 발행 카테고리 (이 목록에 없으면 기본값 '기타' 사용)
VALID_CATEGORIES = ("건강식품", "생활용품", "가전제품", "유아/출산", "기타")

"""
Supabase paid_members 테이블: supabase_schema.sql 참고
users 테이블: 추천인(referrer_id) 정보 — distribute_keyword, distribute_category
"""


def _get_client():
    """Supabase 클라이언트 (anon key)"""
    return get_client(use_service_role=False)


def _get_service_client():
    """RLS 우회용 service_role 클라이언트"""
    return get_client(use_service_role=True)


def fetch_referrer(referrer_username: str, log=None):
    """
    users 테이블에서 추천인 정보를 조회합니다.
    referrer_username = users.username (추천인 아이디)

    Returns:
        dict | None: 추천인 정보 (paid_members와 동일 형식)
            {
                "name": str,
                "keywords": list[str],
                "category": str,
                "coupang_access_key": str,
                "coupang_secret_key": str,
            }
        None: 추천인 없음, 데이터 비어있음, API 키 없음
    """
    _log = log or print
    if not referrer_username or not (referrer_username or "").strip():
        return None

    referrer_username = (referrer_username or "").strip()
    try:
        client = _get_service_client()
        r = (
            client.table("users")
            .select("username, distribute_keyword, distribute_category, coupang_access_key, coupang_secret_key")
            .eq("username", referrer_username)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            _log(f"[Supabase] 추천인 '{referrer_username}' 조회 결과 없음")
            return None

        row = r.data[0]
        raw_kw = (row.get("distribute_keyword") or "").strip()
        kw_list = [k.strip() for k in raw_kw.split(",") if k.strip()]
        if not kw_list:
            _log(f"[Supabase] 추천인 '{referrer_username}' — 키워드가 등록되어 있지 않습니다.")
            return None

        ak = (row.get("coupang_access_key") or "").strip()
        sk = (row.get("coupang_secret_key") or "").strip()
        if not ak or not sk:
            _log(f"[Supabase] 추천인 '{referrer_username}' — 쿠팡 API 키 없음")
            return None

        raw_cat = (row.get("distribute_category") or "").strip()
        category = raw_cat if raw_cat in VALID_CATEGORIES else "기타"

        _log(f"[Supabase] 추천인 '{referrer_username}' 로드 완료")
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
    """
    profiles 테이블에서 본인(로그인 사용자)의 쿠팡 API 키를 조회합니다.
    SaaS 대시보드에서 저장한 값을 사용합니다.
    username 또는 user_id로 조회. user_id 우선 (profiles.id 또는 profiles.user_id = auth.users.id).

    Returns:
        tuple[str, str] | None: (access_key, secret_key) 또는 None (키 없음/오류)
    """
    _log = log or print
    uid = (user_id or "").strip()
    un = (username or "").strip()
    if not uid and not un:
        return None
    try:
        client = _get_service_client()
        r = None
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
    """
    Supabase banned_brands 테이블에서 쿠팡 활동금지 업체/브랜드 목록을 가져옵니다.

    Returns:
        list[str]: 금지 브랜드명 리스트 (예: ["락토핏", "종근당", ...])
        빈 리스트: 데이터 없거나 오류 발생 시
    """
    _log = log or print
    try:
        client = _get_client()
        r = client.table("banned_brands").select("brand_name").execute()
        brands = [row.get("brand_name", "").strip() for row in (r.data or []) if row.get("brand_name", "").strip()]
        if brands:
            _log(f"[Supabase] 활동금지 브랜드 {len(brands)}개 로드")
        return brands
    except Exception as e:
        _log(f"[Supabase] banned_brands 조회 실패: {e}")
        return []


def fetch_banners(log=None):
    """
    Supabase banners 테이블에서 하단 배너 목록을 가져옵니다.

    Returns:
        list[dict]: [{main_text, sub_text, url}, ...]
        빈 리스트: 데이터 없거나 오류 발생 시
    """
    _log = log or print
    try:
        client = _get_client()
        r = client.table("banners").select("main_text, sub_text, url").execute()
        banners = []
        for row in (r.data or []):
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


def fetch_helper_cafes(log=None):
    """
    Supabase helper_cafes 테이블에서 도우미 기본 카페리스트를 가져옵니다.

    Returns:
        list[dict]: [{"cafe_url", "cafe_id", "menu_id", "created_at"}, ...]
        빈 리스트: 데이터 없거나 오류 발생 시
    """
    _log = log or print
    try:
        client = _get_client()
        r = client.table("helper_cafes").select("cafe_url, cafe_id, menu_id, created_at").order("sort_order").execute()
        cafes = []
        for row in (r.data or []):
            url = (row.get("cafe_url") or "").strip()
            cid = (row.get("cafe_id") or "").strip()
            mid = (row.get("menu_id") or "").strip()
            if url and cid and mid:
                cafes.append({
                    "cafe_url": url, "cafe_id": cid, "menu_id": mid,
                    "created_at": row.get("created_at"),
                })
        if cafes:
            _log(f"[Supabase] 도우미 카페 {len(cafes)}개 로드")
        return cafes
    except Exception as e:
        _log(f"[Supabase] helper_cafes 조회 실패: {e}")
        return []


def upsert_helper_cafe(cafe_url: str, cafe_id: str, menu_id: str, sort_order: int = 0, log=None):
    """
    helper_cafes 테이블: cafe_url이 있으면 cafe_id, menu_id 덮어쓰기 (UPDATE).
    없으면 새로 추가 (INSERT). 같은 cafe_url이 하나만 유지되도록 함.
    service_role 사용 (RLS 우회).

    Returns:
        bool: 성공 시 True, 실패 시 False
    """
    _log = log or print
    url = (cafe_url or "").strip()
    cid = (cafe_id or "").strip()
    mid = (menu_id or "").strip()
    if not url or not cid or not mid:
        _log("[Supabase] helper_cafes 저장 실패: cafe_url, cafe_id, menu_id 필수")
        return False
    try:
        client = _get_service_client()
        # 1) cafe_url이 있는 행이 있으면 UPDATE (덮어쓰기)
        r = client.table("helper_cafes").update({
            "cafe_id": cid,
            "menu_id": mid,
            "sort_order": sort_order,
        }).eq("cafe_url", url).execute()
        if r.data and len(r.data) > 0:
            _log(f"[Supabase] helper_cafes 갱신: {url[:40]}... → cafe_id={cid}, menu_id={mid}")
            return True
        # 2) 없으면 INSERT
        client.table("helper_cafes").insert({
            "cafe_url": url,
            "cafe_id": cid,
            "menu_id": mid,
            "sort_order": sort_order,
        }).execute()
        _log(f"[Supabase] helper_cafes 추가: {cid} / {mid}")
        return True
    except Exception as e:
        _log(f"[Supabase] helper_cafes 저장 실패: {e}")
        return False


def insert_helper_cafe(cafe_url: str, cafe_id: str, menu_id: str, sort_order: int = 0, log=None):
    """upsert_helper_cafe의 별칭 (하위 호환)"""
    return upsert_helper_cafe(cafe_url, cafe_id, menu_id, sort_order, log)


def delete_helper_cafe_by_url(cafe_url: str, log=None):
    """
    helper_cafes 테이블에서 cafe_url에 해당하는 행 삭제.
    service_role 사용 (RLS 우회).

    Returns:
        bool: 성공 시 True, 실패 시 False
    """
    _log = log or print
    url = (cafe_url or "").strip()
    if not url:
        return False
    try:
        client = _get_service_client()
        client.table("helper_cafes").delete().eq("cafe_url", url).execute()
        _log(f"[Supabase] helper_cafes 삭제: {url[:50]}...")
        return True
    except Exception as e:
        _log(f"[Supabase] helper_cafes 삭제 실패: {e}")
        return False


def fetch_cafe_join_policy(log=None):
    """cafe_join_policy id=1 조회. 없으면 기본값 반환.
    service_role 사용 (RLS 우회).
    실제 DB 컬럼명(min_created_year, max_created_year, require_no_recent_posts)과
    표준명(created_year_min 등) 모두 지원."""
    _log = log or print
    try:
        client = _get_service_client()
        r = client.table("cafe_join_policy").select("*").eq("id", 1).limit(1).execute()
        if r.data and len(r.data) > 0:
            row = r.data[0]
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
        return {"run_days": [4, 14, 24], "start_time": "09:00", "created_year_min": 2020, "created_year_max": 2025,
                "recent_post_days": 7, "recent_post_enabled": True, "target_count": 50, "expire_days": 10, "search_keyword": ""}
    except Exception as e:
        _log(f"[Supabase] cafe_join_policy 조회 실패: {e}")
        return {"run_days": [4, 14, 24], "start_time": "09:00", "created_year_min": 2020, "created_year_max": 2025,
                "recent_post_days": 7, "recent_post_enabled": True, "target_count": 50, "expire_days": 10, "search_keyword": ""}


def upsert_cafe_join_policy(policy: dict, log=None):
    """cafe_join_policy id=1 upsert. service_role 사용.
    min_created_year/max_created_year/require_no_recent_posts 또는
    created_year_min/created_year_max/recent_post_enabled 스키마 모두 지원."""
    _log = log or print
    try:
        client = _get_service_client()
        year_min = int(policy.get("created_year_min", 2020))
        year_max = int(policy.get("created_year_max", 2025))
        recent_en = bool(policy.get("recent_post_enabled", True))
        base = {
            "id": 1,
            "run_days": policy.get("run_days", [4, 14, 24]),
            "start_time": (policy.get("start_time") or "09:00").strip() or "09:00",
            "recent_post_days": int(policy.get("recent_post_days", 7)),
            "target_count": int(policy.get("target_count", 50)),
            "search_keyword": (policy.get("search_keyword") or "").strip(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        base_no_time = {k: v for k, v in base.items() if k != "start_time"}
        # 표준 컬럼명 시도 후, 실패 시 실제 DB 컬럼명(min_created_year 등) 또는 start_time 제외로 재시도
        for data in [
            {**base, "created_year_min": year_min, "created_year_max": year_max, "recent_post_enabled": recent_en},
            {**base, "min_created_year": year_min, "max_created_year": year_max, "require_no_recent_posts": recent_en},
            {**base_no_time, "created_year_min": year_min, "created_year_max": year_max, "recent_post_enabled": recent_en},
        ]:
            try:
                client.table("cafe_join_policy").upsert(data, on_conflict="id").execute()
                _log("[Supabase] cafe_join_policy 저장 완료")
                return True
            except Exception as inner:
                if "column" in str(inner).lower() or "does not exist" in str(inner).lower():
                    continue
                raise
        return False
    except Exception as e:
        _log(f"[Supabase] cafe_join_policy 저장 실패: {e}")
        return False


def fetch_program_cafe_lists(program_username=None, naver_id=None, statuses=None, log=None, use_service=False):
    """
    agent_cafe_lists에서 카페 리스트 조회.
    - naver_id 우선: naver_id가 있으면 네이버 아이디별 조회
    - program_username: 없으면 program_username으로 조회 (기존 호환)
    """
    _log = log or print
    statuses = statuses or ["saved", "joined"]
    try:
        client = _get_service_client() if use_service else _get_client()
        q = client.table("agent_cafe_lists").select("cafe_url, cafe_id, menu_id, status").in_("status", statuses).order("created_at")
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


def _is_valid_uuid(s):
    """UUID 형식인지 검사 (빈 문자열/None이면 False)."""
    if not s or not str(s).strip():
        return False
    import re
    return bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", str(s).strip()))


def insert_program_cafe_list(owner_user_id, program_username, cafe_url, cafe_id=None, menu_id=None, status="saved", reject_reason=None, naver_id=None, vm_name=None, log=None):
    """agent_cafe_lists에 insert. naver_id, vm_name 있으면 함께 저장. owner_user_id는 유효한 UUID일 때만 포함."""
    _log = log or print
    try:
        client = _get_service_client()
        data = {
            "program_username": program_username or "",
            "cafe_url": cafe_url,
            "cafe_id": cafe_id or "",
            "menu_id": menu_id or "",
            "status": status,
        }
        if _is_valid_uuid(owner_user_id):
            data["owner_user_id"] = str(owner_user_id).strip()
        if naver_id and str(naver_id).strip():
            data["naver_id"] = str(naver_id).strip()
        if vm_name and str(vm_name).strip():
            data["vm_name"] = str(vm_name).strip()
        if reject_reason is not None:
            data["reject_reason"] = reject_reason
        client.table("agent_cafe_lists").insert(data).execute()
        return True
    except Exception as e:
        _log(f"[Supabase] agent_cafe_lists insert 실패: {e}")
        return False


def update_program_cafe_list_status(cafe_url: str, program_username=None, naver_id=None, status: str = None, reject_reason: str = None, cafe_id=None, menu_id=None, last_posted_at=None, log=None):
    """agent_cafe_lists status 업데이트. naver_id 또는 program_username으로 대상 지정."""
    _log = log or print
    try:
        client = _get_service_client()
        data = {}
        if status is not None:
            data["status"] = status
        if reject_reason is not None:
            data["reject_reason"] = reject_reason
        if cafe_id is not None:
            data["cafe_id"] = cafe_id
        if menu_id is not None:
            data["menu_id"] = menu_id
        if last_posted_at is not None:
            data["last_posted_at"] = last_posted_at
        if not data:
            return True
        q = client.table("agent_cafe_lists").update(data).eq("cafe_url", cafe_url)
        if naver_id and str(naver_id).strip():
            q = q.eq("naver_id", str(naver_id).strip())
        elif program_username and str(program_username).strip():
            q = q.eq("program_username", str(program_username).strip())
        else:
            return False
        q.execute()
        return True
    except Exception as e:
        _log(f"[Supabase] agent_cafe_lists update 실패: {e}")
        return False


def delete_agent_cafe_list(cafe_url: str, naver_id=None, program_username=None, log=None):
    """agent_cafe_lists에서 행 삭제 (글작성 실패 시 등)."""
    _log = log or print
    try:
        client = _get_service_client()
        q = client.table("agent_cafe_lists").delete().eq("cafe_url", cafe_url)
        if naver_id and str(naver_id).strip():
            q = q.eq("naver_id", str(naver_id).strip())
        elif program_username and str(program_username).strip():
            q = q.eq("program_username", str(program_username).strip())
        else:
            return False
        q.execute()
        return True
    except Exception as e:
        _log(f"[Supabase] agent_cafe_lists delete 실패: {e}")
        return False


def delete_expired_agent_cafes(naver_id: str, days: int = 10, log=None):
    """last_posted_at이 days일 이전인 카페 삭제 (10일 경과 자동 삭제)."""
    _log = log or print
    if not naver_id or not str(naver_id).strip():
        return 0
    try:
        from datetime import datetime, timezone, timedelta
        client = _get_service_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        r = client.table("agent_cafe_lists").delete().eq("naver_id", str(naver_id).strip()).lt("last_posted_at", cutoff).execute()
        n = len(r.data) if r.data else 0
        if n > 0:
            _log(f"[Supabase] agent_cafe_lists 10일 경과 {n}건 삭제 (naver_id={naver_id})")
        return n
    except Exception as e:
        _log(f"[Supabase] delete_expired_agent_cafes 실패: {e}")
        return 0


def fetch_agent_cafe_lists_full(naver_id: str, statuses=None, log=None, use_service=True):
    """agent_cafe_lists 전체 행 조회 (cafe_url 포함, last_posted_at 업데이트용)."""
    _log = log or print
    statuses = statuses or ["saved", "joined"]
    try:
        client = _get_service_client() if use_service else _get_client()
        r = client.table("agent_cafe_lists").select("cafe_url, cafe_id, menu_id, last_posted_at").eq("naver_id", str(naver_id).strip()).in_("status", statuses).order("created_at").execute()
        return [{"cafe_url": row.get("cafe_url"), "cafe_id": row.get("cafe_id"), "menu_id": row.get("menu_id"), "last_posted_at": row.get("last_posted_at")} for row in (r.data or [])]
    except Exception as e:
        _log(f"[Supabase] agent_cafe_lists full 조회 실패: {e}")
        return []


def fetch_helper_new_cafe_since(log=None):
    """
    app_links에서 신규 카페 기준일 조회.
    link_key='helper_new_cafe_since', url='2026-02-07' (YYYY-MM-DD)

    Returns:
        str | None: 기준일 문자열 (YYYY-MM-DD), 없으면 None
    """
    _log = log or print
    try:
        client = _get_client()
        r = client.table("app_links").select("url").eq("link_key", "helper_new_cafe_since").limit(1).execute()
        if r.data and len(r.data) > 0:
            val = (r.data[0].get("url") or "").strip()
            if val:
                return val
        return None
    except Exception as e:
        _log(f"[Supabase] helper_new_cafe_since 조회 실패: {e}")
        return None


def fetch_app_links(log=None):
    """
    Supabase app_links 테이블에서 링크 설정을 가져옵니다.
    url 또는 value 컬럼 지원 (스키마에 따라 다름)

    Returns:
        dict: link_key → url/value 매핑
            - inquiry: 문의접수 링크
            - tutorial_video: 프로그램 사용법 영상 링크
            - banner: 하단배너 링크
            - captcha_api_key: 2captcha API 키
        빈 dict: 데이터 없거나 오류 발생 시
    """
    _log = log or print
    try:
        client = _get_client()
        r = client.table("app_links").select("*").execute()
        links = {}
        for row in (r.data or []):
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


def is_keyword_banned(keyword: str, banned_brands: list) -> bool:
    """키워드에 금지 브랜드가 포함되어 있는지 확인 (대소문자 무시)"""
    if not keyword or not banned_brands:
        return False
    kw_lower = keyword.lower()
    return any(b.strip().lower() in kw_lower for b in banned_brands if b and b.strip())


def fetch_paid_members(log=None):
    """
    Supabase에서 active=true인 유료회원 목록을 가져옵니다.

    Returns:
        list[dict]: 각 회원 정보
            {
                "name": str,
                "keywords": list[str],   # 콤마 구분 → 리스트 변환
                "category": str,         # 유효하면 그대로, 없으면 '기타'
                "coupang_access_key": str,
                "coupang_secret_key": str,
            }
        빈 리스트: 데이터 없거나 오류 발생 시
    """
    _log = log or print

    try:
        client = _get_client()
        response = (
            client.table("paid_members")
            .select("name, keywords, category, coupang_access_key, coupang_secret_key")
            .eq("active", True)
            .execute()
        )

        members = []
        for row in response.data:
            # 키워드 문자열을 리스트로 변환 (콤마 구분, 공백 제거)
            raw_kw = row.get("keywords", "")
            kw_list = [k.strip() for k in raw_kw.split(",") if k.strip()]

            if not kw_list:
                _log(f"  [주의] 회원 '{row.get('name', '?')}' — 키워드가 비어있어 건너뜁니다.")
                continue

            ak = row.get("coupang_access_key", "")
            sk = row.get("coupang_secret_key", "")
            if not ak or not sk:
                _log(f"  [주의] 회원 '{row.get('name', '?')}' — 쿠팡 API 키가 비어있어 건너뜁니다.")
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

        _log(f"[Supabase] 유료회원 {len(members)}명 로드 완료")
        return members

    except ImportError as e:
        _log(f"[Supabase] 오류: {e}")
        return []
    except ValueError as e:
        _log(f"[Supabase] 설정 오류: {e}")
        return []
    except Exception as e:
        _log(f"[Supabase] 데이터 조회 실패: {e}")
        return []


def fetch_paid_member_keywords_pool(count=None, log=None):
    """
    유료회원들의 키워드를 모아 랜덤 풀로 반환합니다.
    관리자(okdog)용 — 키워드 설정 없이 유료회원 키워드로 발행할 때 사용.

    Returns:
        list[str]: 랜덤 섞인 키워드 리스트 (회원별 랜덤, 키워드별 랜덤)
        count 지정 시 해당 개수만 반환 (부족하면 중복 허용)
    """
    import random
    _log = log or print
    members = fetch_paid_members(log=_log)
    pool = []
    for m in members:
        kws = m.get("keywords") or []
        for kw in kws:
            if kw and str(kw).strip():
                pool.append(str(kw).strip())
    random.shuffle(pool)
    if not pool:
        return []
    if count and count > 0:
        if len(pool) >= count:
            return pool[:count]
        # 부족하면 중복 허용
        return [random.choice(pool) for _ in range(count)]
    return pool


# ─────────────────────────────────────────────────────────────
# post_logs 테이블 — 포스팅 로그 기록
# ─────────────────────────────────────────────────────────────

def insert_post_log(program_username: str, keyword: str, posting_url: str = None, server_name: str = None, post_type: str = "self", partner_id: str = None, status: str = None, log=None):
    """
    post_logs 테이블에 포스팅 로그를 삽입합니다.

    Args:
        program_username: 프로그램 로그인 사용자명
        keyword: 포스팅 키워드
        posting_url: 포스팅 URL (선택)
        server_name: 서버명 (선택)
        post_type: 글 타입 ('self'|'paid'|'referrer'), 기본값 'self'
        partner_id: 쿠팡 파트너스 아이디(lptag, 예: AF4771282) (선택)
        status: 상태 (예: 'started' — post_logs 테이블에 status 컬럼 필요)
        log: 로그 콜백 (선택)
    """
    _log = log or print
    if post_type not in ("self", "paid", "referrer"):
        post_type = "self"
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("config.py에 SUPABASE_URL / SUPABASE_SERVICE_KEY를 설정하세요.")

    try:
        client = _get_service_client()
        payload = {
            "program_username": program_username,
            "keyword": keyword,
            "posting_url": posting_url,
            "server_name": server_name,
            "post_type": post_type,
            "partner_id": partner_id,
        }
        if status is not None:
            payload["status"] = status
        if OWNER_USER_ID:
            payload["owner_user_id"] = OWNER_USER_ID
        client.table("post_logs").insert(payload).execute()
        _log(f"[Supabase] post_logs 삽입: {program_username} / {keyword}")
    except Exception as e:
        _log(f"[Supabase] post_logs 삽입 실패: {e}")
        raise
