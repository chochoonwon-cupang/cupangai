-- ============================================================
-- profiles: 추천 적립 누적, 관리자 보너스 충전 누적 컬럼 추가
-- ============================================================
-- Supabase SQL Editor에서 실행
-- referral_reward_total: 추천인 적립으로 받은 누적 금액
-- admin_bonus_total: 관리자 보너스충전으로 받은 누적 금액
-- ============================================================

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS referral_reward_total INTEGER DEFAULT 0;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS admin_bonus_total INTEGER DEFAULT 0;

UPDATE public.profiles SET referral_reward_total = COALESCE(referral_reward_total, 0) WHERE referral_reward_total IS NULL;
UPDATE public.profiles SET admin_bonus_total = COALESCE(admin_bonus_total, 0) WHERE admin_bonus_total IS NULL;

COMMENT ON COLUMN public.profiles.referral_reward_total IS '추천인 적립 누적 금액';
COMMENT ON COLUMN public.profiles.admin_bonus_total IS '관리자 보너스충전 누적 금액';
