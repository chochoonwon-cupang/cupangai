-- ============================================================
-- profiles에 이메일 자동 반영 (회원가입 시 auth.users → profiles)
-- ============================================================
-- Supabase SQL Editor에서 실행
-- (profiles에 id 없고 user_id만 있는 경우. user_id에 UNIQUE 필요)
-- ============================================================

-- 1) email 컬럼 추가 (없으면)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email TEXT;

-- 2) 신규 가입 시 profiles에 이메일 포함하여 생성하는 트리거
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (user_id, email)
  VALUES (NEW.id, NEW.email)
  ON CONFLICT (user_id) DO UPDATE SET email = EXCLUDED.email, updated_at = now();
  RETURN NEW;
END;
$$;

-- 기존 트리거 삭제 후 재생성 (중복 방지)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 3) 기존 사용자: auth.users 이메일 → profiles.email 동기화
UPDATE public.profiles p
SET email = u.email, updated_at = now()
FROM auth.users u
WHERE p.user_id = u.id AND (p.email IS NULL OR p.email != u.email);
