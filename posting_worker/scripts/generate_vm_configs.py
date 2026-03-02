#!/usr/bin/env python3
"""
VM 300대용 vm_config.json 생성
생성된 파일을 각 VM의 worker.exe와 같은 폴더에 vm_config.json으로 복사
"""
import json
import uuid
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "vm_configs"
COUNT = 300


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for i in range(1, COUNT + 1):
        vm_name = f"vm-{i:03d}"
        cfg = {
            "VM_ID": str(uuid.uuid4()),
            "VM_NAME": vm_name,
        }
        path = OUTPUT_DIR / f"{vm_name}.json"
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Created {path}")
    print(f"\n총 {COUNT}개 생성됨: vm_configs/ 폴더")
    print("각 VM에 vm-001.json → vm_config.json 으로 복사하여 사용")


if __name__ == "__main__":
    main()
