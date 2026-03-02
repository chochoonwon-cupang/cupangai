-- ============================================================
-- profiles 테이블: 총잔액(balance) + 충전금액(total_charged) 추가
-- ============================================================
-- Supabase SQL Editor에서 실행
-- get_wallet_balance, charge_wallet RPC 포함
-- ============================================================

-- 1) profiles 컬럼 추가
-- (오류 시 아래 한 줄씩 따로 실행해보세요)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS total_charged INTEGER DEFAULT 0;

-- IF NOT EXISTS 미지원 시 대안:
-- DO $$ BEGIN
--   IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='profiles' AND column_name='balance') THEN
--     ALTER TABLE public.profiles ADD COLUMN balance INTEGER DEFAULT 0;
--   END IF;
--   IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='profiles' AND column_name='total_charged') THEN
--     ALTER TABLE public.profiles ADD COLUMN total_charged INTEGER DEFAULT 0;
--   END IF;
-- END $$;

-- 기존 NULL → 0 처리
UPDATE public.profiles SET balance = COALESCE(balance, 0) WHERE balance IS NULL;
UPDATE public.profiles SET total_charged = COALESCE(total_charged, 0) WHERE total_charged IS NULL;

COMMENT ON COLUMN public.profiles.balance IS '총잔액 (현재 사용 가능 금액)';
COMMENT ON COLUMN public.profiles.total_charged IS '누적 충전금액';

-- ============================================================
-- 2) get_wallet_balance: 현재 로그인 사용자의 잔액 반환
-- ============================================================
CREATE OR REPLACE FUNCTION public.get_wallet_balance()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  cur_uid UUID;
  cur_bal INTEGER;
BEGIN
  cur_uid := auth.uid();
  IF cur_uid IS NULL THEN
    RETURN 0;
  END IF;

  SELECT COALESCE(balance, 0) INTO cur_bal
  FROM profiles
  WHERE user_id = cur_uid OR id = cur_uid
  LIMIT 1;

  RETURN COALESCE(cur_bal, 0);
END;
$$;

-- ============================================================
-- 3) charge_wallet: 충전 — balance + total_charged 증가
-- ============================================================
CREATE OR REPLACE FUNCTION public.charge_wallet(p_amount INTEGER)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  cur_uid UUID;
BEGIN
  cur_uid := auth.uid();
  IF cur_uid IS NULL THEN
    RAISE EXCEPTION '로그인이 필요합니다.';
  END IF;
  IF p_amount IS NULL OR p_amount <= 0 THEN
    RAISE EXCEPTION '충전 금액은 0보다 커야 합니다.';
  END IF;

  UPDATE profiles
  SET
    balance = COALESCE(balance, 0) + p_amount,
    total_charged = COALESCE(total_charged, 0) + p_amount,
    updated_at = now()
  WHERE user_id = cur_uid OR id = cur_uid;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'profiles 행이 없습니다. user_id=%', cur_uid;
  END IF;
END;
$$;
