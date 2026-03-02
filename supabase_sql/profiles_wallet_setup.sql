-- ============================================================
-- 잔액/충전 전체 설정 (한 번에 실행)
-- ============================================================
-- Supabase 대시보드 → SQL Editor → 이 전체 내용 붙여넣기 → Run
-- (IF NOT EXISTS 오류 시: 1번 줄을 아래로 교체)
--   ALTER TABLE public.profiles ADD COLUMN balance INTEGER DEFAULT 0;
--   ALTER TABLE public.profiles ADD COLUMN total_charged INTEGER DEFAULT 0;
-- ============================================================

-- 0) 기존 함수 삭제 (column "v" 오류 방지 — 이전 버전 제거)
DROP FUNCTION IF EXISTS public.get_wallet_balance();
DROP FUNCTION IF EXISTS public.charge_wallet(INTEGER);

-- 1) 컬럼 추가 (이미 있으면 오류 → 2번부터 실행)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS balance INTEGER DEFAULT 0;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS total_charged INTEGER DEFAULT 0;

-- 2) get_wallet_balance
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
  IF cur_uid IS NULL THEN RETURN 0; END IF;
  SELECT COALESCE(balance, 0) INTO cur_bal FROM public.profiles WHERE user_id = cur_uid OR id = cur_uid LIMIT 1;
  RETURN COALESCE(cur_bal, 0);
END;
$$;

-- 3) charge_wallet
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
  IF cur_uid IS NULL THEN RAISE EXCEPTION '로그인이 필요합니다.'; END IF;
  IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION '충전 금액은 0보다 커야 합니다.'; END IF;
  UPDATE public.profiles SET balance = COALESCE(balance, 0) + p_amount, total_charged = COALESCE(total_charged, 0) + p_amount, updated_at = now() WHERE user_id = cur_uid OR id = cur_uid;
  IF NOT FOUND THEN RAISE EXCEPTION 'profiles 행이 없습니다.'; END IF;
END;
$$;

-- 4) 권한 부여 (authenticated 사용자가 RPC 호출 가능)
GRANT EXECUTE ON FUNCTION public.get_wallet_balance() TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_wallet_balance() TO anon;
GRANT EXECUTE ON FUNCTION public.charge_wallet(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.charge_wallet(INTEGER) TO anon;
