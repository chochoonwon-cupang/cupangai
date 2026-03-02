# ============================================================
# 회원가입 / 로그인 / 세션 관리
# ============================================================
# Supabase users 테이블 연동, 비밀번호 해싱, 기기 제한
# ============================================================

import hashlib
import secrets
import json
import os
import sys
import uuid
from datetime import datetime, timedelta

# exe 실행 시 exe 위치 기준, 스크립트 실행 시 소스 위치 기준
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, ".auth_session.json")

# Cython 컴파일된 auth_core 사용 (있으면), 없으면 로컬 구현
try:
    from auth_core import _hash_password, _verify_password
except ImportError:
    def _hash_password(password: str) -> str:
        """비밀번호를 salt + SHA256으로 해싱"""
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"{salt}:{h}"

    def _verify_password(password: str, stored: str) -> bool:
        """저장된 해시와 비밀번호 검증"""
        if not stored or ":" not in stored:
            return False
        salt, h = stored.split(":", 1)
        computed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return secrets.compare_digest(computed, h)


def _get_client():
    """Supabase 클라이언트 (service key로 auth 작업) — configs/app_config.json 기반"""
    from shared.sb import get_client
    return get_client(use_service_role=True)


def register(username: str, password: str, referral_username: str = None, log=None) -> tuple[bool, str]:
    """
    회원가입.
    Returns: (성공여부, 메시지)
    """
    _log = log or print
    username = (username or "").strip()
    password = (password or "").strip()
    referral_username = (referral_username or "").strip() or None

    if not username or len(username) < 2:
        return False, "아이디는 2자 이상이어야 합니다."
    if not password or len(password) < 4:
        return False, "비밀번호는 4자 이상이어야 합니다."

    try:
        client = _get_client()
        # 중복 체크
        r = client.table("users").select("id").eq("username", username).execute()
        if r.data and len(r.data) > 0:
            return False, "이미 사용 중인 아이디입니다."

        free_until = (datetime.utcnow() + timedelta(days=180)).strftime("%Y-%m-%d")  # +6개월
        pw_hash = _hash_password(password)

        row = {
            "username": username,
            "password_hash": pw_hash,
            "max_devices": 5,
            "free_use_until": free_until,
            "referral_count": 0,
            "agreed_to_terms": True,
        }
        if referral_username:
            row["referrer_id"] = referral_username

        try:
            client.table("users").insert(row).execute()
        except Exception as insert_err:
            err_str = str(insert_err).lower()
            if "column" in err_str or "schema" in err_str or "bod_to_terms" in err_str or "agreed_to_terms" in err_str:
                del row["agreed_to_terms"]
                client.table("users").insert(row).execute()
            else:
                raise insert_err

        # 추천인 처리
        if referral_username:
            ref = client.table("users").select("id, referral_count").eq("username", referral_username).execute()
            if ref.data and len(ref.data) > 0:
                ref_id = ref.data[0]["id"]
                ref_count = ref.data[0].get("referral_count", 0) or 0
                client.table("users").update({"referral_count": ref_count + 1}).eq("id", ref_id).execute()

        _log(f"[회원가입] 성공: {username}")
        return True, "회원가입이 완료되었습니다. 로그인해주세요."
    except Exception as e:
        _log(f"[회원가입] 오류: {e}")
        return False, str(e)


def _resolve_email_from_input(client, input_str: str, log=None) -> str | None:
    """
    입력이 이메일(@ 포함)이면 그대로 반환.
    아니면 profiles에서 username 또는 login_id로 email 조회.
    """
    _log = log or print
    s = (input_str or "").strip()
    if not s:
        return None
    if "@" in s:
        return s
    try:
        # profiles에 username 또는 login_id 컬럼으로 email 조회
        for col in ("username", "login_id"):
            try:
                r = client.table("profiles").select("email").eq(col, s).limit(1).execute()
                if r.data and len(r.data) > 0:
                    email = (r.data[0].get("email") or "").strip()
                    if email:
                        return email
            except Exception:
                continue
    except Exception as e:
        _log(f"[로그인] profiles 조회 실패: {e}")
    return None


def login(username_or_email: str, password: str, log=None) -> tuple[bool, str, dict]:
    """
    Supabase Auth(email/password) 로그인.
    - 입력이 이메일이 아니면 profiles에서 username/login_id로 email 조회
    - profiles에 user_id row 없으면 자동 생성
    Returns: (성공여부, 메시지, 사용자정보 또는 None)
    """
    _log = log or print
    username_or_email = (username_or_email or "").strip()
    password = (password or "").strip()
    if not username_or_email or not password:
        return False, "아이디와 비밀번호를 입력하세요.", None

    try:
        from shared.sb import get_client
        client = get_client(use_service_role=True)
        email = _resolve_email_from_input(client, username_or_email, log=_log)
        if not email:
            return False, "아이디 또는 이메일을 찾을 수 없습니다. 이메일로 로그인해주세요.", None

        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if not res or not res.user:
            return False, "아이디 또는 비밀번호가 올바르지 않습니다.", None

        user_id = str(res.user.id)
        user_email = (res.user.email or email).strip()

        # profiles에 row 없으면 자동 생성
        from datetime import datetime
        try:
            now_iso = datetime.utcnow().isoformat()
            client.table("profiles").upsert(
                {"id": user_id, "email": user_email, "updated_at": now_iso},
                on_conflict="id",
            ).execute()
        except Exception as upsert_err:
            try:
                client.table("profiles").insert({
                    "id": user_id,
                    "email": user_email,
                    "created_at": datetime.utcnow().isoformat(),
                }).execute()
            except Exception:
                pass

        user = {
            "id": user_id,
            "username": username_or_email if "@" not in username_or_email else user_email,
            "email": user_email,
        }
        _save_session(user)
        _log(f"[로그인] 성공: {user_email}")
        return True, "로그인되었습니다.", user
    except Exception as e:
        err_str = str(e).lower()
        if "invalid" in err_str or "credentials" in err_str or "email" in err_str:
            return False, "아이디 또는 비밀번호가 올바르지 않습니다.", None
        _log(f"[로그인] 오류: {e}")
        return False, str(e), None


def logout(log=None):
    """로그아웃 - 세션 삭제"""
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass
    if log:
        log("[로그아웃] 완료")


def _save_session(user: dict):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(user, f, ensure_ascii=False, indent=2)


def get_session() -> dict | None:
    """저장된 로그인 세션 반환. 없으면 None"""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def is_logged_in() -> bool:
    return get_session() is not None


def get_free_use_until() -> str:
    s = get_session()
    return (s.get("free_use_until") or "")[:10] if s else ""


# ============================================================
# 쿠팡 키 저장 및 active_sessions (기기 제한)
# ============================================================

# 유효한 발행 카테고리 (추천인 distribute_category용)
VALID_CATEGORIES = ("건강식품", "생활용품", "가전제품", "유아/출산", "기타")


def update_distribute_keywords(user_id: str, keywords_str: str, category_str: str = None, log=None) -> tuple[bool, str]:
    """
    추천인 포스팅 발행용 키워드·카테고리를 profiles에 저장.
    keywords_str: 콤마(,)로 구분된 키워드 문자열 (한 줄)
    category_str: 발행 카테고리 (유효하지 않으면 '기타')
    Returns: (성공여부, 메시지)
    """
    _log = log or print
    try:
        client = _get_client()
        data = {"distribute_keyword": (keywords_str or "").strip(), "updated_at": datetime.utcnow().isoformat()}
        if category_str is not None:
            raw = (category_str or "").strip()
            data["distribute_category"] = raw if raw in VALID_CATEGORIES else "기타"
        client.table("profiles").update(data).eq("id", user_id).execute()
        _log("[추천인 키워드·카테고리] 저장 완료")
        return True, "저장되었습니다."
    except Exception as e:
        _log(f"[추천인 키워드] 저장 실패: {e}")
        return False, str(e)


def get_distribute_keywords(user_id: str, log=None) -> str:
    """저장된 distribute_keyword 반환 (profiles)"""
    _log = log or print
    try:
        client = _get_client()
        r = client.table("profiles").select("distribute_keyword").eq("id", user_id).execute()
        if r.data and len(r.data) > 0:
            return r.data[0].get("distribute_keyword") or ""
    except Exception as e:
        _log(f"[추천인 키워드] 조회 실패: {e}")
    return ""


def get_distribute_category(user_id: str, log=None) -> str:
    """저장된 distribute_category 반환 (profiles, 유효하지 않으면 '기타')"""
    _log = log or print
    try:
        client = _get_client()
        r = client.table("profiles").select("distribute_category").eq("id", user_id).execute()
        if r.data and len(r.data) > 0:
            raw = (r.data[0].get("distribute_category") or "").strip()
            return raw if raw in VALID_CATEGORIES else "기타"
    except Exception as e:
        _log(f"[추천인 카테고리] 조회 실패: {e}")
    return "기타"


def save_coupang_keys(user_id: str, access_key: str, secret_key: str, log=None) -> tuple[bool, str]:
    """
    로그인 사용자의 쿠팡 키를 profiles에 저장.
    Returns: (성공여부, 메시지)
    """
    _log = log or print
    try:
        client = _get_client()
        client.table("profiles").update({
            "coupang_access_key": access_key,
            "coupang_secret_key": secret_key,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()
        _log("[쿠팡키] 저장 완료")
        return True, "저장됨"
    except Exception as e:
        _log(f"[쿠팡키] 저장 실패: {e}")
        return False, str(e)


def check_device_limit(access_key: str, user_id: str, max_devices: int, log=None) -> tuple[bool, str]:
    """
    해당 Access Key 사용 중인 active_sessions 수가 max_devices 초과인지 확인.
    active_sessions 테이블 없으면 (PGRST205 등) 오류 시 일단 허용.
    Returns: (허용여부, 메시지)
    """
    _log = log or print
    if not access_key or not user_id:
        return False, "쿠팡 API 키를 입력하세요."
    try:
        client = _get_client()
        r = client.table("active_sessions").select("id").eq("coupang_access_key", access_key).execute()
        count = len(r.data) if r.data else 0
        if count >= max_devices:
            return False, f"실행 허용 대수 초과 (최대 {max_devices}대)"
        return True, ""
    except Exception as e:
        _log(f"[기기체크] 오류(무시): {e}")
        return True, ""  # 테이블 없음 등 — 세션 기능 비활성화, 진행 허용


def add_active_session(user_id: str, access_key: str, secret_key: str, log=None) -> tuple[bool, str]:
    """
    실행 시작 시 active_sessions에 세션 추가.
    active_sessions 테이블 없으면 (PGRST205 등) 실패해도 (True, None) 반환 — 진행 허용.
    Returns: (성공여부, session_id 또는 None)
    """
    _log = log or print
    try:
        client = _get_client()
        sid = str(uuid.uuid4())
        client.table("active_sessions").insert({
            "id": sid,
            "user_id": user_id,
            "coupang_access_key": access_key,
            "coupang_secret_key": secret_key,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
        return True, sid
    except Exception as e:
        _log(f"[세션추가] 오류(무시, 진행 허용): {e}")
        return True, None  # 테이블 없음 등 — 세션 기능 비활성화, 실행은 허용


def remove_active_session(session_id: str, log=None):
    """실행 종료/앱 종료 시 세션 제거. active_sessions 없으면 무시."""
    if not session_id:
        return
    _log = log or print
    try:
        client = _get_client()
        client.table("active_sessions").delete().eq("id", session_id).execute()
    except Exception as e:
        _log(f"[세션제거] 오류(무시): {e}")
