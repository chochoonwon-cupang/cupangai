# ============================================================
# 쿠팡 파트너스 봇 - 설정 파일
# ============================================================
# 각 API 키를 본인의 키로 교체하세요.
# 실서비스에서는 .env 파일이나 환경변수로 관리하는 것을 권장합니다.
# ============================================================

import os

# ── SaaS 소유자 UID (post_logs.owner_user_id) ──
# Supabase auth.uid() 또는 users.id 값. 환경변수 OWNER_USER_ID 또는 config.json
_owner = os.getenv("OWNER_USER_ID", "")
if not _owner:
    try:
        import json
        _cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.isfile(_cfg):
            with open(_cfg, "r", encoding="utf-8") as f:
                _owner = (json.load(f) or {}).get("OWNER_USER_ID", "") or ""
    except Exception:
        pass
OWNER_USER_ID = (_owner or "").strip()

# ── 쿠팡 파트너스 API ──
# GUI에서 사용자가 직접 입력합니다.
ACCESS_KEY = ""
SECRET_KEY = ""

# ── Google Gemini API ──
# https://aistudio.google.com/app/apikey 에서 발급
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# ── Bitly 단축 링크 API ──
# https://app.bitly.com/settings/api/ 에서 발급
BITLY_ACCESS_TOKEN = "YOUR_BITLY_ACCESS_TOKEN"

# ── 커스텀 리다이렉트 도메인 ──
# 가비아+Vercel 연결된 리다이렉트 주소
REDIRECT_BASE_URL = "https://go.kdgc.co.kr/go"

# ── Supabase (configs/app_config.json에서 로드) ──
# Supabase 설정은 configs/app_config.json에서만 관리합니다.
def _load_supabase_from_config():
    try:
        from shared.sb import load_config
        c = load_config()
        return c.get("SUPABASE_URL", ""), c.get("SUPABASE_ANON_KEY", ""), c.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except Exception:
        return "", "", ""
_sb_url, _sb_anon, _sb_svc = _load_supabase_from_config()
SUPABASE_URL = _sb_url
SUPABASE_ANON_KEY = _sb_anon
SUPABASE_SERVICE_KEY = _sb_svc  # auth.py 등에서 사용

# ── 기본 설정 ──
IMAGE_SAVE_DIR = "images"           # 이미지 저장 폴더
DEFAULT_SEARCH_LIMIT = 5            # 기본 검색 결과 수
