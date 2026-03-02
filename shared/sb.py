# ============================================================
# 공통 Supabase 클라이언트 — configs/app_config.json 기반
# ============================================================
# gui.py, posting_worker 모두 이 모듈을 import해서 사용
# ============================================================

import os
import json
from typing import Optional

from supabase import create_client, Client


def _project_root():
    """프로젝트 루트 (쿠팡사용자 폴더) 경로"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config_path():
    return os.path.join(_project_root(), "configs", "app_config.json")


_config_error: Optional[str] = None


def load_config() -> Optional[dict]:
    """
    configs/app_config.json 읽기
    Returns:
        dict: {"PROJECT", "SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"}
        None: SUPABASE_URL 또는 SUPABASE_ANON_KEY 없으면 (예외 메시지는 _config_error)
    """
    global _config_error
    _config_error = None
    path = _config_path()
    if not os.path.isfile(path):
        _config_error = f"configs/app_config.json이 없습니다. 경로: {path}"
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        _config_error = f"configs/app_config.json 파싱 실패: {e}"
        return None

    url = str(data.get("SUPABASE_URL") or "").strip().rstrip("/")
    anon_key = str(data.get("SUPABASE_ANON_KEY") or "").strip()

    if not url or not anon_key:
        _config_error = (
            "configs/app_config.json에 SUPABASE_URL과 SUPABASE_ANON_KEY를 설정하세요. "
            f"(현재: SUPABASE_URL={'설정됨' if url else '없음'}, ANON_KEY={'설정됨' if anon_key else '없음'})"
        )
        return None

    return {
        "PROJECT": str(data.get("PROJECT") or "").strip(),
        "SUPABASE_URL": url,
        "SUPABASE_ANON_KEY": anon_key,
        "SUPABASE_SERVICE_ROLE_KEY": str(data.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip(),
    }


# 클라이언트 캐시 (1번만 생성)
_client_anon: Optional[Client] = None
_client_service: Optional[Client] = None


def get_client(use_service_role: bool = False) -> Client:
    """
    Supabase 클라이언트 (캐시 사용, 1번만 생성)
    """
    global _client_anon, _client_service
    cfg = load_config()
    if cfg is None:
        raise ValueError(_config_error or "load_config()가 None을 반환했습니다.")

    if use_service_role:
        if _client_service is None:
            key = cfg.get("SUPABASE_SERVICE_ROLE_KEY") or ""
            if not key:
                raise ValueError("configs/app_config.json에 SUPABASE_SERVICE_ROLE_KEY를 설정하세요.")
            _client_service = create_client(cfg["SUPABASE_URL"], key)
        return _client_service
    else:
        if _client_anon is None:
            _client_anon = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_ANON_KEY"])
        return _client_anon


def rpc(name: str, payload: dict, use_service_role: bool = False, log=None) -> tuple:
    """
    RPC 호출 유틸
    Returns:
        tuple: (ok: bool, data, err: str)
        실패 시 (False, None, err_msg)
    """
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=use_service_role)
        result = client.rpc(name, payload).execute()
        return True, result.data, ""
    except Exception as e:
        err = str(e)
        _log(f"[Supabase] RPC {name} 실패: {err}")
        return False, None, err


def select(
    table: str,
    filters: dict = None,
    columns: str = "*",
    order: str = None,
    limit: int = None,
    log=None,
) -> list:
    """
    간단 select 유틸
    Args:
        table: 테이블명
        filters: {"col": value} — eq로 적용
        columns: "col1, col2" 또는 "*"
        order: "created_at.desc"
        limit: 최대 행 수
    Returns:
        list[dict] 또는 []
    """
    _log = log or (lambda m: None)
    try:
        client = get_client(use_service_role=False)
        q = client.table(table).select(columns)
        if filters:
            for col, val in filters.items():
                q = q.eq(col, val)
        if order:
            parts = order.split(".")
            if len(parts) == 2:
                q = q.order(parts[0], desc=(parts[1].lower() == "desc"))
            else:
                q = q.order(order)
        if limit:
            q = q.limit(limit)
        r = q.execute()
        return list(r.data or [])
    except Exception as e:
        _log(f"[Supabase] select {table} 실패: {e}")
        return []


def fetch_vm_accounts(vm_name: str, log=None) -> list:
    """
    vm_accounts 테이블에서 VM별 네이버 계정 로드
    - table: vm_accounts
    - where vm_name == 입력값
    - naver_accounts jsonb를 list로 반환
    - 없으면 [] 반환
    """
    _log = log or (lambda m: None)
    try:
        rows = select("vm_accounts", filters={"vm_name": vm_name}, columns="naver_accounts", limit=1, log=_log)
        if not rows:
            return []
        raw = rows[0].get("naver_accounts")
        if isinstance(raw, list):
            return raw
        return []
    except Exception as e:
        _log(f"[Supabase] fetch_vm_accounts({vm_name}) 실패: {e}")
        return []
