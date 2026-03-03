-- ============================================================
-- naver_id 테이블 — VM별 네이버 로그인 계정 (통신모드용)
-- ============================================================
-- VM 이름별로 네이버 아이디/비밀번호 저장. 통신모드 글작성 시 사용.
-- 관리자 페이지 > 작업아이디설정에서 등록/수정/삭제.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.naver_id (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vm_name TEXT NOT NULL,
  login_id TEXT NOT NULL,
  password TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  daily_blog_limit INT NOT NULL DEFAULT 0,
  daily_cafe_limit INT NOT NULL DEFAULT 0,
  daily_blog_used INT NOT NULL DEFAULT 0,
  daily_cafe_used INT NOT NULL DEFAULT 0,
  usage_date DATE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(vm_name, login_id)
);

COMMENT ON TABLE public.naver_id IS 'VM별 네이버 로그인 계정 (통신모드 글작성용)';
COMMENT ON COLUMN public.naver_id.vm_name IS 'VM 이름 (예: vm-001, autocoupang-web-02)';
COMMENT ON COLUMN public.naver_id.login_id IS '네이버 로그인 아이디';
COMMENT ON COLUMN public.naver_id.password IS '네이버 비밀번호';
COMMENT ON COLUMN public.naver_id.is_active IS 'true=사용, false=사용대기';
COMMENT ON COLUMN public.naver_id.daily_blog_limit IS '하루 블로그 발행 한도 (0=무제한)';
COMMENT ON COLUMN public.naver_id.daily_cafe_limit IS '하루 카페 발행 한도 (0=무제한)';

-- RLS: 관리자 페이지에서만 접근 (앱에서 is_admin 체크)
ALTER TABLE public.naver_id ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow read naver_id" ON public.naver_id;
DROP POLICY IF EXISTS "Allow all naver_id for service" ON public.naver_id;
CREATE POLICY "Allow all naver_id" ON public.naver_id FOR ALL USING (true);

CREATE INDEX IF NOT EXISTS idx_naver_id_vm_name ON public.naver_id(vm_name);
CREATE INDEX IF NOT EXISTS idx_naver_id_is_active ON public.naver_id(is_active) WHERE is_active = true;
