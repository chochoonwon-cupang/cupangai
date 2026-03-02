-- ============================================================
-- profiles에 user_id 컬럼 추가 (대시보드 호환)
-- ============================================================
-- 대시보드가 .eq("user_id", auth.user.id)로 조회하므로 user_id 필요
-- id = auth.users.id, user_id = id 로 동기화
-- ============================================================

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- 기존 행: user_id = id 로 채우기
UPDATE public.profiles SET user_id = id WHERE user_id IS NULL AND id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON public.profiles(user_id) WHERE user_id IS NOT NULL;
