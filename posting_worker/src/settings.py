# ============================================================
# Settings — 환경변수 및 설정 로드
# ============================================================
# .env 파일 지원 (python-dotenv)
# ============================================================

import os

# .env 로드 시도
try:
    from dotenv import load_dotenv
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _env_path = os.path.join(_ROOT, ".env")
    load_dotenv(_env_path)
except ImportError:
    pass


class Settings:
    """환경변수 기반 설정 (dotenv 로드 후)"""

    # Supabase
    SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or ""
    VM_TOKEN = os.environ.get("VM_TOKEN") or ""

    # 워커 모드
    WORKER_MODE = os.environ.get("WORKER_MODE", "server")  # server | local
    WORKER_NAME = os.environ.get("WORKER_NAME", "vm-001")
    WORKER_DEFAULT_JOB = os.environ.get("WORKER_DEFAULT_JOB", "placeholder")
    WORKER_REQUEUE_INTERVAL_SEC = int(os.environ.get("WORKER_REQUEUE_INTERVAL_SEC", "60"))
    WORKER_STUCK_REQUEUE_SEC = int(os.environ.get("WORKER_STUCK_REQUEUE_SEC", "600"))
    WORKER_HEARTBEAT_SEC = int(os.environ.get("WORKER_HEARTBEAT_SEC", "30"))
    WORKER_CLAIM_INTERVAL_SEC = int(os.environ.get("WORKER_CLAIM_INTERVAL_SEC", "2"))
    WORKER_MAX_CONCURRENCY = int(os.environ.get("WORKER_MAX_CONCURRENCY", "1"))

    # 레거시 호환
    WORKER_SLEEP_SEC = int(os.environ.get("WORKER_SLEEP_SEC", "3"))
    WORKER_POLL_INTERVAL = int(os.environ.get("WORKER_POLL_INTERVAL", "5"))


# 싱글톤 인스턴스
settings = Settings()
