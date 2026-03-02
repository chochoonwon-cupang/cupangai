-- ============================================================
-- agent_cafe_lists: naver_id, vm_name 컬럼 추가
-- 네이버 아이디별 카페 리스트, 가입 VM 추적
-- Supabase SQL Editor에서 실행
-- ============================================================

-- naver_id: 네이버 로그인 아이디 (카페 가입/글작성 계정별 그룹핑)
ALTER TABLE agent_cafe_lists ADD COLUMN IF NOT EXISTS naver_id TEXT;

-- vm_name: 가입을 수행한 VM 이름 (예: vm-001)
ALTER TABLE agent_cafe_lists ADD COLUMN IF NOT EXISTS vm_name TEXT;

-- last_posted_at: 마지막 글 작성 시각 (10일 경과 삭제용)
ALTER TABLE agent_cafe_lists ADD COLUMN IF NOT EXISTS last_posted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_naver_id ON agent_cafe_lists(naver_id);
CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_vm_name ON agent_cafe_lists(vm_name);
