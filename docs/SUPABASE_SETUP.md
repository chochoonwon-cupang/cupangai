# Supabase 설정 통합 가이드

## 1. 실행 방법

### GUI 실행
```powershell
cd "c:\Users\USER\Desktop\쿠팡사용자"
python gui.py
```

### Posting Worker 실행
```powershell
cd "c:\Users\USER\Desktop\쿠팡사용자"
python posting_worker/worker_entry.py
```
- `vm_config.json`이 `posting_worker/` 폴더에 있어야 함
- `configs/app_config.json`이 프로젝트 루트에 있어야 함

---

## 2. 오류 시 로그 확인 위치

| 대상 | 로그 위치 |
|------|----------|
| GUI | 콘솔 출력 (시작 시 `[GUI] PROJECT=..., SUPABASE_URL=...` 등) |
| Posting Worker | `posting_worker/logs/worker.log` |

### GUI 시작 시 출력 예시
```
[GUI] PROJECT=main-production, SUPABASE_URL=https://vdyliufqshfdhvjshdfa.supabase.co
[GUI] get_admin_settings=OK, get_cafe_targets=OK
```

### 오류 발생 시 확인 사항
1. **config 로드 실패**: `configs/app_config.json` 존재 여부, JSON 형식
2. **Supabase 연결 실패**: `SUPABASE_URL`, `SUPABASE_ANON_KEY` 값 확인
3. **get_admin_settings FAIL**: `app_links` 테이블 존재 여부
4. **get_cafe_targets FAIL**: `helper_cafes` 테이블 존재 여부

---

## 3. Supabase 필요한 테이블 / RPC

### 테이블
| 테이블 | 용도 |
|--------|------|
| `users` | 사용자(쿠팡 키, distribute_keyword 등) |
| `app_links` | 관리자 설정 (gemini_api_key, captcha_api_key 등) |
| `helper_cafes` | 카페 타겟 (cafe_id, menu_id, cafe_url) |
| `vm_accounts` | VM별 네이버 계정 (vm_name, naver_accounts) |
| `banned_brands` | 금지 브랜드 |
| `paid_members` | 유료회원 |
| `agent_configs` | 에이전트 설정 |
| `agent_cafe_lists` | 에이전트 카페 리스트 (naver_id별, vm_name 추적) |
| `cafe_join_policy` | 카페 자동가입 정책 (검색 기반 run_cafe_join_job) |

### app_links 등록 예시 (관리자 설정)
```sql
INSERT INTO app_links (link_key, url) VALUES
  ('gemini_api_key', 'YOUR_GEMINI_API_KEY'),
  ('captcha_api_key', 'YOUR_2CAPTCHA_API_KEY')
ON CONFLICT (link_key) DO UPDATE SET url = EXCLUDED.url;
```

### vm_accounts 등록 예시
```sql
INSERT INTO vm_accounts (vm_name, naver_accounts) VALUES
  ('vm-001', '[{"id":"naver_id1","pw":"password1"},{"id":"naver_id2","pw":"password2"}]')
ON CONFLICT (vm_name) DO UPDATE SET naver_accounts = EXCLUDED.naver_accounts, updated_at = now();
```

### RPC (posting_worker용)
| RPC | 용도 |
|-----|------|
| `claim_task` | 작업 선점 |
| `finish_task` | 작업 완료 |
| `fail_task` | 작업 실패 |
| `heartbeat_vm` | VM 생존 신호 |
| `heartbeat_task` | 작업 lease 연장 |
| `requeue_stuck_tasks` | stuck 작업 복구 |

### RPC (카페 자동가입 정책 — 어드민 전용)
| RPC | 용도 |
|-----|------|
| `admin_get_cafe_join_policy` | 검색 기반 카페 가입 정책 조회 |
| `admin_upsert_cafe_join_policy` | 검색 기반 카페 가입 정책 저장 |

**설정 방법**: `supabase_cafe_join_flow.sql`을 Supabase SQL Editor에서 실행.

### agent_cafe_lists (naver_id, vm_name)
- `naver_id`: 네이버 로그인 아이디별 카페 리스트
- `vm_name`: 가입 수행 VM
- `last_posted_at`: 마지막 글 작성 시각 (10일 경과 삭제용)

**마이그레이션**: `supabase_agent_cafe_lists_naver_vm.sql` 실행.

---

## 4. 선택 테이블 (있으면 사용)

| 테이블 | 용도 |
|--------|------|
| `user_keywords` | 사용자별 키워드 (user_id, keyword) |
| `admin_keywords` | 관리자 키워드 풀 (없으면 paid_members 키워드 사용) |

`user_keywords`가 없으면 빈 리스트 반환 후 `admin_keywords` 또는 `paid_members` 키워드로 fallback.
