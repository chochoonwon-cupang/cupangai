-- ============================================================
-- profiles 테이블에 balance, total_charged 컬럼 추가
-- ============================================================
-- Supabase SQL Editor에서 실행
-- (이미 컬럼 있으면 "already exists" 오류 → 무시하고 RPC만 실행)
-- ============================================================

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS total_charged INTEGER DEFAULT 0;
