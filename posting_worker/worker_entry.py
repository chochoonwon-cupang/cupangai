import os
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가 (shared.sb 등 import용)
def _project_root():
    bd = Path(__file__).parent if not getattr(sys, "frozen", False) else Path(sys.executable).parent
    return bd.parent
if str(_project_root()) not in sys.path:
    sys.path.insert(0, str(_project_root()))

from src.main import main


def base_dir():
    """posting_worker 폴더 경로"""
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def project_root():
    """메인 프로젝트 루트 (쿠팡사용자 폴더) — configs/app_config.json 위치"""
    bd = base_dir()
    # posting_worker/worker_entry.py → parent = 프로젝트 루트
    return bd.parent


def load_json(name: str):
    p = base_dir() / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_app_config():
    """configs/app_config.json 로드 (메인 프로젝트 통일)"""
    p = project_root() / "configs" / "app_config.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


if __name__ == "__main__":
    vm = load_json("vm_config.json")
    app = load_app_config()  # configs/app_config.json (프로젝트 루트)

    # ✅ app_config.json → 환경변수 주입
    os.environ.setdefault("SUPABASE_URL", str(app.get("SUPABASE_URL", "")).strip())
    os.environ.setdefault("SUPABASE_ANON_KEY", str(app.get("SUPABASE_ANON_KEY", "")).strip())

    os.environ["ROLE"] = "worker"
    os.environ["VM_ID"] = str(vm.get("VM_ID", "")).strip()
    os.environ["VM_NAME"] = str(vm.get("VM_NAME", "")).strip()

    if not os.environ["VM_ID"]:
        raise SystemExit("VM_ID가 비어있습니다. vm_config.json에 VM_ID를 넣어주세요 (uuid).")
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_ANON_KEY"):
        raise SystemExit("SUPABASE_URL 또는 SUPABASE_ANON_KEY 미설정 (configs/app_config.json 확인)")

    main()
