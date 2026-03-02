-- ============================================================
-- get_wallet_balance, charge_wallet RPC 생성
-- ============================================================
-- Supabase 대시보드 → SQL Editor → 새 쿼리 → 이 전체 내용 붙여넣기 → Run
-- ============================================================

-- 기존 함수 삭제 후 재생성 (column "v" 오류 방지)
DROP FUNCTION IF EXISTS public.get_wallet_balance();
DROP FUNCTION IF EXISTS public.charge_wallet(INTEGER);

-- 1) get_wallet_balance: 현재 로그인 사용자의 잔액 반환
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
  FROM public.profiles
  WHERE user_id = cur_uid OR id = cur_uid
  LIMIT 1;

  RETURN COALESCE(cur_bal, 0);
END;
$$;

-- 2) charge_wallet: 충전 — balance + total_charged 동시 증가
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

  UPDATE public.profiles
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

-- 권한 부여
GRANT EXECUTE ON FUNCTION public.get_wallet_balance() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_wallet_balance() TO anon;
GRANT EXECUTE ON FUNCTION public.charge_wallet(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.charge_wallet(INTEGER) TO anon;
