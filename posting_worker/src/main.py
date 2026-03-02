# ============================================================
# Posting Worker — 메인 진입점
# ============================================================
# 1) vm_identity에서 vm_id 로드/생성
# 2) Settings 로드 (.env)
# 3) worker_loop.start_worker 실행
# 4) logs/worker.log 기록
# ============================================================

import os
import socket
import time
from datetime import datetime
from pathlib import Path

# .env 경로 명시 로드 (parents[1] = posting_worker/)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

# posting_worker 루트
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# VM별 네이버 계정 (vm_accounts에서 로드)
_vm_naver_accounts = []
_LOGS_DIR = os.path.join(_ROOT, "logs")
_LOG_FILE = None


def _ensure_logs_dir():
    os.makedirs(_LOGS_DIR, exist_ok=True)


def _open_log_file():
    """로그 파일 열기 (worker.log)"""
    global _LOG_FILE
    _ensure_logs_dir()
    path = os.path.join(_LOGS_DIR, "worker.log")
    _LOG_FILE = open(path, "a", encoding="utf-8")
    return _LOG_FILE


def _log(msg: str):
    """콘솔 + worker.log 동시 출력 (flush=True로 EXE에서 즉시 출력)"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _LOG_FILE:
        _LOG_FILE.write(line + "\n")
        _LOG_FILE.flush()


def run_leader_loop():
    """리더 전용: requeue만 실행, claim 안 함"""
    REQUEUE_EVERY_SEC = int(os.getenv("REQUEUE_EVERY_SEC", "10"))
    WORKER_STUCK_REQUEUE_SEC = int(os.getenv("WORKER_STUCK_REQUEUE_SEC", "120"))
    from .vm_identity import get_vm_name
    vm_name = get_vm_name()
    _log(f"[LEADER] vm_name={vm_name} requeue-only mode ON (every {REQUEUE_EVERY_SEC}s, stuck>{WORKER_STUCK_REQUEUE_SEC}s)")
    from . import supabase_client
    try:
        while True:
            try:
                ok, data, err = supabase_client.requeue_stuck_tasks(WORKER_STUCK_REQUEUE_SEC, log=_log)
                cnt = (data if isinstance(data, int) else (data.get("count", 0) if isinstance(data, dict) else 0)) if ok else 0
                _log(f"[LEADER] requeue_stuck_tasks({WORKER_STUCK_REQUEUE_SEC}) -> {cnt}")
            except Exception as e:
                _log(f"[LEADER] requeue error: {e}")
            _log(f"[LEADER] 대기중... (다음 requeue까지 {REQUEUE_EVERY_SEC}s)")
            time.sleep(REQUEUE_EVERY_SEC)
    except KeyboardInterrupt:
        _log("[LEADER] KeyboardInterrupt — 종료")


def load_vm_accounts(vm_name: str, log=None):
    """[D] VM_NAME으로 vm_accounts에서 네이버 계정 로드"""
    global _vm_naver_accounts
    _log_fn = log if log else _log
    try:
        from shared.sb import fetch_vm_accounts
        _vm_naver_accounts = fetch_vm_accounts(vm_name, log=_log_fn)
        if _vm_naver_accounts:
            _log_fn(f"[Worker] vm_accounts 로드: {vm_name} → {len(_vm_naver_accounts)}개 계정")
        return _vm_naver_accounts
    except Exception as e:
        _log_fn(f"[Worker] vm_accounts 로드 실패: {e}")
        _vm_naver_accounts = []
        return []


def get_vm_naver_accounts():
    """로드된 VM 네이버 계정 반환"""
    return _vm_naver_accounts


def run_worker_loop():
    """워커: claim/execute"""
    from .vm_identity import get_or_create_vm_id, get_vm_name
    vm_id = get_or_create_vm_id()
    vm_name = get_vm_name()
    load_vm_accounts(vm_name, log=_log)
    from .worker_loop import start_worker, set_stop_flag
    try:
        start_worker(vm_id=vm_id, vm_name=vm_name, log_callback=_log)
    except KeyboardInterrupt:
        set_stop_flag(True)
        _log("KeyboardInterrupt — 종료 중")


def main():
    # 0) env 체크 (load_dotenv는 상단에서 이미 실행됨)
    from .settings import settings
    print("[ENV CHECK] TEST_SLEEP_SEC =", os.getenv("TEST_SLEEP_SEC"), flush=True)
    print("[ENV CHECK] WORKER_STUCK_REQUEUE_SEC =", os.getenv("WORKER_STUCK_REQUEUE_SEC"), flush=True)
    print("[ENV CHECK] WORKER_REQUEUE_INTERVAL_SEC =", os.getenv("WORKER_REQUEUE_INTERVAL_SEC"), flush=True)

    # 1) 로그 파일 열기
    _open_log_file()

    # 2) vm_id, vm_name 로드 (BOOT 로그용)
    from .vm_identity import get_or_create_vm_id, get_vm_name
    vm_id = get_or_create_vm_id()
    vm_name = get_vm_name()

    ROLE = os.getenv("ROLE", "worker").strip().lower()
    REQUEUE_EVERY_SEC = int(os.getenv("REQUEUE_EVERY_SEC", "10"))
    WORKER_STUCK_REQUEUE_SEC = int(os.getenv("WORKER_STUCK_REQUEUE_SEC", "120"))
    _log(f"[BOOT] vm_id={vm_id} vm_name={vm_name} pid={os.getpid()} host={socket.gethostname()} ROLE={ROLE} stuck={WORKER_STUCK_REQUEUE_SEC}s requeue_every={REQUEUE_EVERY_SEC}s")

    # 3) Settings 로드
    _log(f"WORKER_MODE={settings.WORKER_MODE} SUPABASE_URL={bool(settings.SUPABASE_URL)}")

    # 4) ROLE에 따라 분기
    if ROLE == "leader":
        try:
            run_leader_loop()
        finally:
            if _LOG_FILE:
                _LOG_FILE.close()
    else:
        try:
            run_worker_loop()
        finally:
            if _LOG_FILE:
                _LOG_FILE.close()


if __name__ == "__main__":
    main()
