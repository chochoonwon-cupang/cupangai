-- ============================================================
-- 수동 되돌리기: get_wallet_balance, charge_wallet 제거
-- ============================================================
-- Supabase SQL Editor에서 실행
-- ============================================================

-- 1) 함수 삭제
DROP FUNCTION IF EXISTS public.get_wallet_balance();
DROP FUNCTION IF EXISTS public.charge_wallet(INTEGER);

-- 2) 컬럼 삭제 (필요할 때만 실행 — 대시보드 잔액 기능 사용 안 할 때)
-- ALTER TABLE public.profiles DROP COLUMN IF EXISTS balance;
-- ALTER TABLE public.profiles DROP COLUMN IF EXISTS total_charged;
