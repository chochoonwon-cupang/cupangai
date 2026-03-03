-- ============================================================
-- naver_id — 아이디별 일일 발행 한도 (블로그/카페)
-- ============================================================
-- daily_blog_limit, daily_cafe_limit: 0 = 무제한
-- usage_date: 당일 사용량 기준일 (날짜 바뀌면 used 초기화)
-- ============================================================

ALTER TABLE public.naver_id
  ADD COLUMN IF NOT EXISTS daily_blog_limit INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS daily_cafe_limit INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS daily_blog_used INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS daily_cafe_used INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS usage_date DATE;

COMMENT ON COLUMN public.naver_id.daily_blog_limit IS '하루 블로그 발행 한도 (0=무제한)';
COMMENT ON COLUMN public.naver_id.daily_cafe_limit IS '하루 카페 발행 한도 (0=무제한)';
COMMENT ON COLUMN public.naver_id.daily_blog_used IS '당일 블로그 발행 사용량';
COMMENT ON COLUMN public.naver_id.daily_cafe_used IS '당일 카페 발행 사용량';
COMMENT ON COLUMN public.naver_id.usage_date IS '사용량 기준일 (날짜 바뀌면 used 초기화)';
