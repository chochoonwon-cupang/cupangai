-- ============================================================
-- 관리자: 사용자별 금액 조회 (아이디, 잔액, 충전, 포스팅비용, 추천보너스, 관리자보너스)
-- ============================================================
-- Supabase SQL Editor에서 실행
-- is_admin() RPC 필요
-- ============================================================

DROP FUNCTION IF EXISTS public.admin_get_user_balances(text);

CREATE OR REPLACE FUNCTION public.admin_get_user_balances(p_search TEXT DEFAULT NULL)
RETURNS TABLE (
  user_id UUID,
  email TEXT,
  balance INTEGER,
  total_charged INTEGER,
  cost_per_post INTEGER,
  referral_reward_total INTEGER,
  admin_bonus_total INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT (SELECT is_admin()) THEN
    RAISE EXCEPTION '관리자만 실행 가능합니다.';
  END IF;

  RETURN QUERY
  SELECT
    p.user_id,
    p.email,
    COALESCE(p.balance, 0)::INTEGER AS balance,
    COALESCE(p.total_charged, 0)::INTEGER AS total_charged,
    COALESCE(p.cost_per_post, 70)::INTEGER AS cost_per_post,
    COALESCE(p.referral_reward_total, 0)::INTEGER AS referral_reward_total,
    COALESCE(p.admin_bonus_total, 0)::INTEGER AS admin_bonus_total
  FROM public.profiles p
  WHERE (p_search IS NULL OR trim(p_search) = '')
     OR (p.email ILIKE '%' || trim(p_search) || '%')
     OR (p.user_id::TEXT ILIKE '%' || trim(p_search) || '%')
  ORDER BY p.email ASC NULLS LAST;
END;
$$;

GRANT EXECUTE ON FUNCTION public.admin_get_user_balances(text) TO authenticated;
