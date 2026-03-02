-- ============================================================
-- 관리자 보너스충전: 이메일로 특정 유저에게 충전금액 지급
-- ============================================================
-- Supabase SQL Editor에서 실행
-- is_admin() RPC 필요
-- profiles.admin_bonus_total 누적
-- ============================================================

DROP FUNCTION IF EXISTS public.admin_charge_user_by_email(text, integer);

CREATE OR REPLACE FUNCTION public.admin_charge_user_by_email(p_email TEXT, p_amount INTEGER)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid UUID;
  v_updated INT;
BEGIN
  IF NOT (SELECT is_admin()) THEN
    RAISE EXCEPTION '관리자만 실행 가능합니다.';
  END IF;
  IF p_email IS NULL OR trim(p_email) = '' THEN
    RAISE EXCEPTION '이메일을 입력해주세요.';
  END IF;
  IF p_amount IS NULL OR p_amount <= 0 THEN
    RAISE EXCEPTION '충전 금액은 0보다 커야 합니다.';
  END IF;

  SELECT id INTO v_uid FROM auth.users WHERE email = trim(p_email) LIMIT 1;
  IF v_uid IS NULL THEN
    RETURN jsonb_build_object('success', false, 'message', '해당 이메일 사용자를 찾을 수 없습니다.');
  END IF;

  UPDATE public.profiles
  SET
    balance = COALESCE(balance, 0) + p_amount,
    total_charged = COALESCE(total_charged, 0) + p_amount,
    admin_bonus_total = COALESCE(admin_bonus_total, 0) + p_amount,
    updated_at = now()
  WHERE user_id = v_uid;

  GET DIAGNOSTICS v_updated = ROW_COUNT;
  IF v_updated = 0 THEN
    RETURN jsonb_build_object('success', false, 'message', 'profiles 행이 없습니다.');
  END IF;

  RETURN jsonb_build_object('success', true, 'message', p_amount || '원 보너스충전 완료');
END;
$$;

GRANT EXECUTE ON FUNCTION public.admin_charge_user_by_email(text, integer) TO authenticated;
