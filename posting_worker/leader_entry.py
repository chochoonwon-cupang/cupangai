import os
from src.main import main

if __name__ == "__main__":
    os.environ["ROLE"] = "leader"
    # leader는 VM_ID/VM_NAME 없어도 되지만, 로그 추적용으로 박아도 됨
    os.environ.setdefault("VM_NAME", "leader")
    os.environ.setdefault("VM_ID", os.environ.get("VM_ID", ""))
    main()
