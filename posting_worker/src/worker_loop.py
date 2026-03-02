# ============================================================
# Worker Loop — Supabase 작업 큐 폴링 및 처리
# ============================================================
# 상태머신: (A) heartbeat (B) requeue_stuck (C) claim+execute (D) default_job
# ============================================================

import os
import threading
import time

from .settings import settings
from . import supabase_client
from . import posting_logic

# stop_flag: True가 되면 루프 종료
_stop_flag = False


def set_stop_flag(value: bool = True):
    global _stop_flag
    _stop_flag = value


def get_stop_flag() -> bool:
    return _stop_flag


def start_worker(vm_id: str, vm_name: str, log_callback=None):
    """
    무한 루프로 작업을 폴링하고 처리합니다.
    (A) heartbeat 주기 체크
    (B) requeue_stuck_tasks 주기 호출
    (C) claim_task → execute_task
    (D) task 없으면 run_default_job
    """
    log = log_callback or print
    log(f"[Worker] 시작 vm_id={vm_id} vm_name={vm_name}")

    last_heartbeat = 0.0
    last_requeue_ts = 0.0
    heartbeat_sec = settings.WORKER_HEARTBEAT_SEC
    claim_interval = settings.WORKER_CLAIM_INTERVAL_SEC

    while not get_stop_flag():
        try:
            now = time.time()

            # (A) heartbeat 주기 체크
            if now - last_heartbeat >= heartbeat_sec:
                supabase_client.heartbeat_vm(vm_id, vm_name, log=log)
                last_heartbeat = now

            # (B) periodic requeue (only leader) — DB 과부하 방지
            leader_vm = os.getenv("REQUEUE_LEADER_VM", "vm-001")
            requeue_every_sec = int(os.getenv("REQUEUE_EVERY_SEC", "30"))
            stuck_sec = int(os.getenv("WORKER_STUCK_REQUEUE_SEC", "120"))
            if vm_name == leader_vm:
                if now - last_requeue_ts >= requeue_every_sec:
                    try:
                        ok, data, err = supabase_client.requeue_stuck_tasks(stuck_sec, log=log)
                        n = data if isinstance(data, int) else (data.get("count", 0) if isinstance(data, dict) else 0) if ok else 0
                        log(f"[requeue] ran requeue_stuck_tasks({stuck_sec}) -> {n} tasks")
                    except Exception as e:
                        log(f"[requeue] error: {e}")
                    last_requeue_ts = now

            # (C) claim_task 호출
            task = supabase_client.claim_task(vm_id, log=log)

            if task:
                task_id = task.get("id")
                log(f"[CLAIMED] vm_id={vm_id} task_id={task_id}")
                if task_id is None:
                    log("[Worker] claim_task 반환에 id 없음 — 스킵")
                else:
                    log(f"[Worker] claimed task id={task_id} keys={list(task.keys())}")
                    execute_task(task, vm_id, vm_name, log)
                # task 처리 후 바로 다음 루프 (claim_interval 무시)
                continue

            # (D) task 없으면 run_default_job
            run_default_job(log)

        except Exception as e:
            log(f"[Worker] 루프 오류: {e}")

        # 대기
        log("[Worker] 대기중... (pending 작업 없음)")
        sleep_sec = max(claim_interval, 1)
        for _ in range(sleep_sec):
            if get_stop_flag():
                break
            time.sleep(1)

    log("[Worker] 종료됨")


HEARTBEAT_EVERY_SEC = int(os.getenv("WORKER_HEARTBEAT_EVERY_SEC", "30"))
LEASE_SEC = int(os.getenv("WORKER_LEASE_SEC", "420"))


def _maybe_heartbeat_task(task_id, vm_id: str, vm_name: str, last_ping: list, log):
    """작업 중 30초마다 heartbeat_task 호출 (lease 연장)"""
    now = time.time()
    if now - last_ping[0] >= HEARTBEAT_EVERY_SEC:
        supabase_client.heartbeat_task(task_id, vm_id, LEASE_SEC, vm_name, log=log)
        last_ping[0] = now


def execute_task(task: dict, vm_id: str, vm_name: str, log):
    """
    task 처리: posting_logic.run 호출 후 finish_task / fail_task
    작업 중 HEARTBEAT_EVERY_SEC마다 heartbeat_task로 lease 연장
    """
    task_id = task.get("id")
    platform = task.get("platform", "cafe")
    from .posting_logic import _get_keyword_from_task
    keyword = _get_keyword_from_task(task)

    log(f"[Worker] 작업 시작 task_id={task_id} platform={platform} using keyword={keyword!r}")
    start_ms = time.time() * 1000

    result = None
    task_error = None

    def _run_task():
        nonlocal result, task_error
        try:
            # claim 직후 — finish_task 전에 슬립 (assigned로 오래 남게)
            test_sleep = int(os.getenv("TEST_SLEEP_SEC", "0"))
            log(f"[SLEEP CHECK] before posting, TEST_SLEEP_SEC={test_sleep}")
            if test_sleep > 0:
                log(f"[SLEEP CHECK] sleeping {test_sleep}s now...")
                time.sleep(test_sleep)
                log("[SLEEP CHECK] woke up")

            result = posting_logic.run(task)
        except KeyboardInterrupt:
            task_error = "KeyboardInterrupt"
            raise
        except Exception as e:
            task_error = str(e)

    try:
        last_ping = [0.0]

        th = threading.Thread(target=_run_task, daemon=True)
        th.start()

        while th.is_alive():
            _maybe_heartbeat_task(task_id, vm_id, vm_name, last_ping, log)
            time.sleep(min(HEARTBEAT_EVERY_SEC, 5))

        th.join(timeout=0.1)

        if task_error == "KeyboardInterrupt":
            log("[Worker] KeyboardInterrupt - DO NOT finish_task. exiting now.")
            raise KeyboardInterrupt

        if task_error:
            log(f"[Worker] error: {task_error}")
            supabase_client.fail_task(vm_id, task_id, task_error, last_step="execute", log=log)
            return

        if result is None:
            log("[Worker] result is None — fail_task")
            supabase_client.fail_task(vm_id, task_id, "result is None", last_step="execute", log=log)
            return

        elapsed_ms = int((time.time() * 1000) - start_ms)
        log(f"[Worker] 작업 처리 시간 {elapsed_ms}ms")

        if result.get("ok"):
            result_url = result.get("result_url", "") or "OK"
            supabase_client.finish_task(vm_id, task_id, result_url, log=log)
            log(f"[Worker] 작업 완료 task_id={task_id} result_url={result_url}")
        else:
            err = result.get("error", "unknown")
            last_step = result.get("last_step", "unknown")
            supabase_client.fail_task(vm_id, task_id, err, last_step=last_step, log=log)
            log(f"[Worker] 작업 실패 task_id={task_id} error={err}")

    except KeyboardInterrupt:
        log("[Worker] KeyboardInterrupt - DO NOT finish_task. exiting now.")
        raise

    except Exception as e:
        log(f"[Worker] error: {e}")
        supabase_client.fail_task(vm_id, task_id, str(e), last_step="execute", log=log)


def run_default_job(log):
    """서버에 작업이 없을 때 기본작업 — VM 카페 포스팅 (vm_accounts 계정별)"""
    try:
        from .vm_identity import get_vm_name
        from . import main as _main
        vm_name = get_vm_name()
        accounts = _main.get_vm_naver_accounts()
        if accounts and len(accounts) > 0:
            from . import vm_cafe_posting
            log("[Worker] VM 카페 포스팅 사이클 시작")
            vm_cafe_posting.run_vm_cafe_cycle(vm_name, accounts, log=log)
            log("[Worker] VM 카페 포스팅 사이클 완료")
        else:
            log("[Worker] vm_accounts 없음 — placeholder")
    except ImportError as e:
        log(f"[Worker] vm_cafe_posting import 실패: {e}")
    except Exception as e:
        log(f"[Worker] run_default_job 오류: {e}")
