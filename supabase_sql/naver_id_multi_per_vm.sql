-- ============================================================
-- naver_id 테이블 — VM당 여러 계정 허용 (마이그레이션)
-- ============================================================
-- 기존: VM당 1개 (UNIQUE vm_name)
-- 변경: VM당 여러 개, 동일 VM 내 login_id 중복 불가 (UNIQUE vm_name,login_id)
-- 사용: VM당 is_active=true인 계정 1개만 작업에 사용
-- ============================================================

-- 1. 기존 UNIQUE(vm_name) 제거
ALTER TABLE public.naver_id DROP CONSTRAINT IF EXISTS naver_id_vm_name_key;

-- 2. VM+아이디 조합 유니크 (같은 VM에 같은 아이디 중복 방지)
ALTER TABLE public.naver_id DROP CONSTRAINT IF EXISTS naver_id_vm_name_login_id_key;
ALTER TABLE public.naver_id ADD CONSTRAINT naver_id_vm_name_login_id_key UNIQUE (vm_name, login_id);

-- 3. VM당 is_active=true 1개만 허용 (트리거 또는 앱 로직)
-- 앱에서 저장 시 해당 VM의 다른 계정 is_active=false 처리
