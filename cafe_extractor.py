# ============================================================
# 네이버 카페 URL → 카페 ID / 메뉴 ID 추출
# ============================================================
# requests로 카페 페이지를 가져와 HTML에서 clubid, menuid 파싱
# ============================================================

import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


def extract_cafe_info(cafe_url: str, timeout: int = 10, html: str | None = None):
    """
    네이버 카페 URL에서 카페 ID와 메뉴 목록을 추출합니다.

    Args:
        cafe_url: 네이버 카페 URL (예: https://cafe.naver.com/jo/741450)
        timeout: 요청 타임아웃(초)
        html: HTML 문자열 (제공 시 요청 생략, Selenium page_source 등)

    Returns:
        dict: {
            "cafe_id": str or None,
            "menus": [{"menu_name": str, "menu_id": str, "type": str}, ...],
            "error": str or None
        }
    """
    url = (cafe_url or "").strip()
    if not url:
        return {"cafe_id": None, "menus": [], "error": "URL을 입력해주세요."}

    if "cafe.naver.com" not in url:
        return {"cafe_id": None, "menus": [], "error": "네이버 카페 URL이 아닙니다."}

    if html is not None and html.strip():
        pass  # html 사용
    else:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            return {"cafe_id": None, "menus": [], "error": f"페이지 요청 실패: {e}"}

    # 1. clubid 추출 (cafe_id)
    cafe_id = None
    for pat in [
        r'["\']?clubid["\']?\s*[:=]\s*["\']?(\d+)',
        r'search\.clubid=(\d+)',
        r'clubid=(\d+)',
        r'clubId=(\d+)',
        r'/cafes/(\d+)',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            cafe_id = m.group(1)
            break

    # 2. 메뉴 목록 추출 (menuid=XXX, menu_name)
    menus = []
    seen = set()

    # [메뉴명](URL...search.menuid=XXX...) 마크다운/링크 형태 (메뉴명+menuid 동시 추출)
    for m in re.finditer(
        r'\[([^\]]+)\]\([^)]*search\.menuid=(\d+)[^)]*\)',
        html,
    ):
        name, mid = m.group(1).strip(), m.group(2)
        if mid not in seen and name and len(name) < 50:
            seen.add(mid)
            menus.append({"menu_name": name, "menu_id": mid, "type": "일반"})

    # <a ...>메뉴명</a> 내부에 href에 menuid 있는 경우
    for m in re.finditer(
        r'<a[^>]*href="[^"]*search\.menuid=(\d+)[^"]*"[^>]*>([^<]+)</a>',
        html,
        re.IGNORECASE,
    ):
        mid, name = m.group(1), m.group(2).strip()
        if mid not in seen and name and len(name) < 50 and not name.startswith("http"):
            seen.add(mid)
            menus.append({"menu_name": name, "menu_id": mid, "type": "일반"})

    # JSON 형태: "menuId":32,"menuName":"공지사항"
    for m in re.finditer(
        r'["\']?menu_?[iI]d["\']?\s*:\s*["\']?(\d+)["\']?\s*[,}][^}]*["\']?(?:menu_?[nN]ame|name|title)["\']?\s*:\s*["\']([^"\']+)["\']',
        html,
    ):
        mid, name = m.group(1), m.group(2).strip()
        if mid not in seen:
            seen.add(mid)
            menus.append({"menu_name": name, "menu_id": mid, "type": "일반"})

    # menuid만 있는 경우 (메뉴명 없음) - 마지막에 추가
    for m in re.finditer(
        r'search\.menuid=(\d+)|menuid=(\d+)|menu_id=(\d+)|menus/(\d+)|/cafes/\d+/menus/(\d+)',
        html,
        re.IGNORECASE,
    ):
        mid = m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5)
        if mid and mid not in seen:
            seen.add(mid)
            menus.append({"menu_name": mid, "menu_id": mid, "type": "일반"})

    # 중복 제거 후 정렬 (menu_id 숫자순)
    def sort_key(x):
        try:
            return int(x["menu_id"])
        except ValueError:
            return 0

    menus = sorted(menus, key=sort_key)

    # 메뉴가 없으면 기본 게시판(전체글) 추가 시도
    if not menus and cafe_id:
        menus.append({"menu_name": "전체글", "menu_id": "0", "type": "일반"})

    return {"cafe_id": cafe_id, "menus": menus, "error": None}


def extract_cafe_created_year(html: str) -> int | None:
    """
    HTML에서 카페 개설년도만 추출. 못 찾으면 None.
    ia-info-data / div.thm 내 'YYYY.MM.DD. 개설' 형식 우선 검사.
    """
    import re
    for pat in [
        r'ia-info-data[\s\S]*?(\d{4})\.\d{1,2}\.\d{1,2}\.\s*개설',
        r'class="thm"[^>]*>[\s\S]*?(\d{4})\.\d{1,2}\.\d{1,2}\.\s*개설',
        r'(\d{4})[.\-]\d{1,2}[.\-]\d{1,2}\.\s*개설',
        r'개설[일]?\s*[:：]?\s*(\d{4})',
        r'생성[일]?\s*[:：]?\s*(\d{4})',
        r'created[_\s]?year["\']?\s*[:=]\s*["\']?(\d{4})',
        r'(\d{4})\s*년\s*개설',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def check_cafe_created_year(html: str, year_min: int, year_max: int) -> bool | None:
    """
    HTML에서 카페 개설년도 추출. year_min~year_max 범위면 True, 밖이면 False, 못 찾으면 None.
    """
    y = extract_cafe_created_year(html)
    if y is None:
        return None
    return year_min <= y <= year_max


def check_no_recent_post(html: str, within_days: int = 7) -> bool | None:
    """
    HTML에서 최근 게시물 날짜 확인. within_days 이내 글이 없으면 True, 있으면 False, 못 찾으면 None.
    """
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=within_days)
    found_any = False
    for m in re.finditer(r'(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})', html):
        try:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            dt = datetime(y, mo, d)
            found_any = True
            if dt >= cutoff:
                return False  # 최근 글 있음 → 탈락
        except (ValueError, IndexError):
            continue
    return True if found_any else None  # 날짜 못 찾으면 None


def fetch_article_list_html(cafe_id: str, menu_id: str = "0", timeout: int = 10) -> str:
    """전체글보기(ArticleList) 페이지 HTML 반환. cafe_id 필수.
    구형(ArticleList.nhn)과 신형(/f-e/cafes/...) URL 모두 시도."""
    if not cafe_id:
        return ""
    urls = [
        f"https://cafe.naver.com/ArticleList.nhn?search.clubid={cafe_id}&search.menuid={menu_id}",
        f"https://cafe.naver.com/f-e/cafes/{cafe_id}/menus/{menu_id}",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception:
            continue
    return ""


# 메뉴 추출 시 제외할 메뉴명 (포함 시 제외)
EXCLUDE_MENU_KEYWORDS = (
    "전체글보기", "인기글", "카페태그", "카페캘린더", "카페북", "책꽃이",
    "공지사항", "가입인사", "출석체크", "카페앨범",
)


def pick_best_menu_id(menus: list, exclude_notice: bool = True) -> str | None:
    """
    메뉴 목록에서 포스팅용 menu_id를 선택합니다.

    - 제외: 전체글보기, 인기글, 카페태그, 카페캘린더, 카페북, 책꽃이,
            공지사항, 가입인사, 출석체크, 카페앨범
    - 우선: 자유, 일반, 질문, 건의 포함 메뉴
    - 해당 없으면 첫 번째 유효 메뉴 반환

    Returns:
        str | None: 선택된 menu_id, 없으면 None
    """
    if not menus:
        return None

    def is_excluded(name: str) -> bool:
        for kw in EXCLUDE_MENU_KEYWORDS:
            if kw in name:
                return True
        return False

    filtered = []
    for m in menus:
        name = (m.get("menu_name") or "").strip()
        if is_excluded(name):
            continue
        mid = (m.get("menu_id") or "").strip()
        if not mid:
            continue
        if mid == "0":
            continue
        filtered.append(m)

    if not filtered:
        return None

    # 우선 키워드: 자유, 일반, 질문, 건의
    priority = ["자유", "일반", "질문", "건의"]
    for kw in priority:
        for m in filtered:
            name = (m.get("menu_name") or "").strip()
            if kw in name:
                return m.get("menu_id")
    return filtered[0].get("menu_id")
