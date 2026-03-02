# ============================================================
# VM Identity — 워커 식별자 로드/생성
# ============================================================
# VM_ID env 우선, 없으면 data/vm_id.txt
# VM_NAME env 우선, 없으면 기본값
# ============================================================

import os
import uuid

# posting_worker 루트 기준 (src의 상위)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VM_ID_FILE = os.path.join(_ROOT, "data", "vm_id.txt")


def get_or_create_vm_id() -> str:
    """
    VM ID를 반환합니다.
    - VM_ID env가 있으면 그 uuid 사용
    - 없으면 data/vm_id.txt에서 로드
    - 없으면 새 UUID 생성 후 저장
    """
    vid = (os.environ.get("VM_ID") or "").strip()
    if vid:
        return vid
    os.makedirs(os.path.dirname(VM_ID_FILE), exist_ok=True)
    if os.path.isfile(VM_ID_FILE):
        with open(VM_ID_FILE, "r", encoding="utf-8") as f:
            vid = (f.read() or "").strip()
        if vid:
            return vid
    vid = str(uuid.uuid4())
    with open(VM_ID_FILE, "w", encoding="utf-8") as f:
        f.write(vid)
    return vid


def get_vm_name() -> str:
    """
    VM 이름을 반환합니다.
    - VM_NAME env가 있으면 그 값 사용
    - 없으면 WORKER_NAME env
    - 없으면 기본값 vm-test
    """
    name = (os.environ.get("VM_NAME") or os.environ.get("WORKER_NAME") or "").strip()
    return name if name else "vm-test"
