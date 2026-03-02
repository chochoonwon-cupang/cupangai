# Posting Worker

Supabase `post_tasks` 테이블을 폴링하여 포스팅 작업을 처리하는 Python 워커입니다.

## 실행 플로우

1. **GUI**: "실행 시작" 버튼 → `enqueue_post_tasks` RPC 호출 → `post_tasks`에 pending 상태 row 생성
2. **Worker**: `post_tasks`에서 `pending` → `claim` → `assigned` → 포스팅 실행 → `finish` 또는 `fail`
3. GUI는 worker 상태를 직접 제어하지 않으며, `post_tasks` 상태만 모니터링(나중에 추가 가능)

## 채널별 핸들러

- `channel='cafe'` / `channel='blog'`: 기본 포스팅 (posting_logic)
- `channel='cafe_autojoin'`: 카페 자동가입 (cafe_autojoin_handler) — task.meta에 owner_user_id, program_username, naver_id, naver_pw, captcha_api_key, accounts, immediate 포함

## VM 카페 포스팅 (run_default_job)

서버에 task가 없을 때 `vm_accounts`의 네이버 계정별로:

1. **10일 경과 카페 삭제**: last_posted_at이 10일 이전인 카페 agent_cafe_lists에서 삭제
2. **50개 유지**: 카페 수 < 50이면 run_cafe_join_job으로 부족분 가입
3. **1건 포스팅**: last_posted_at 오래된 카페에 글 작성
4. **성공**: last_posted_at 갱신
5. **실패**: 해당 카페 agent_cafe_lists에서 삭제

필요: `vm_accounts` (vm_name별 naver_accounts), `agent_cafe_lists`, `cafe_join_policy`, `app_links` (gemini_api_key), `users` (COMM_USERNAME의 쿠팡 키)

## 구조

```
posting_worker/
  src/
    main.py             # 진입점
    worker_loop.py      # 작업 폴링 루프
    supabase_client.py  # Supabase RPC
    vm_identity.py      # VM ID 관리
    vm_cafe_posting.py  # VM 카페 포스팅 (50개 유지, 10일 삭제)
    posting_logic.py   # 포스팅 실행
    settings.py        # 설정 로드
  data/                 # vm_id.txt 등
  profiles/
  logs/                 # 로그 파일
```

## 실행

```bash
cd posting_worker
pip install -r requirements.txt
cp .env.example .env
# .env 편집 후
python -m src.main
```

## 환경변수

- `SUPABASE_URL` — Supabase 프로젝트 URL
- `SUPABASE_ANON_KEY` — anon key
- `VM_TOKEN` — (선택) 워커 인증
- `WORKER_SLEEP_SEC` — 폴링 간격(초)
