# ============================================================
# 도우미 카페 자동 가입 모듈
# ============================================================
# 서버(helper_cafes)에서 카페리스트를 불러와 자동 가입
# 포스팅도우미(posting_help) 로직 참고
# ============================================================

import time

# naver_id별 검색 결과 캐시 (다 사용할 때까지 재사용, 다 쓰면 새 키워드로 검색)
_search_cache = {}
import base64
import random
import requests

# Selenium 지연 로드
By = None
EC = None
Keys = None
WebDriverWait = None
TimeoutException = None


def _ensure_selenium():
    global By, EC, Keys, WebDriverWait, TimeoutException
    if By is not None:
        return
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.common.keys import Keys as _Keys
    from selenium.webdriver.support import expected_conditions as _EC
    from selenium.webdriver.support.ui import WebDriverWait as _WDW
    from selenium.common.exceptions import TimeoutException as _TE
    By = _By
    EC = _EC
    Keys = _Keys
    WebDriverWait = _WDW
    TimeoutException = _TE


def _solve_captcha(captcha_image_url, api_key, log=None):
    """2captcha API로 캡챠 해독 (base64 우선, 실패 시 url 방식)"""
    _log = log or print
    if not api_key or not api_key.strip():
        return None

    def _poll_result(task_id, api_key, max_wait=120):
        res_url = "https://2captcha.com/res.php"
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(5)
            wait_time += 5
            try:
                resp = requests.get(
                    res_url,
                    params={"key": api_key.strip(), "action": "get", "id": task_id},
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                result = resp.text.strip()
                if result.startswith("OK|"):
                    return result.split("|")[1]
                if result == "CAPCHA_NOT_READY":
                    continue
                _log(f"[캡챠 API] 해독 실패: {result}")
                return None
            except Exception:
                continue
        return None

    key = api_key.strip()
    task_id = None
    if (captcha_image_url or "").startswith("/"):
        captcha_image_url = "https://cafe.naver.com" + captcha_image_url

    # 1) base64 방식 시도
    try:
        if (captcha_image_url or "").startswith("data:"):
            import re
            m = re.search(r"base64,(.+)", captcha_image_url)
            image_base64 = m.group(1) if m else ""
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://cafe.naver.com/",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }
            img_resp = requests.get(captcha_image_url, headers=headers, timeout=10)
            img_resp.raise_for_status()
            image_data = img_resp.content
            if len(image_data) == 0:
                raise ValueError("이미지 비어있음")
            image_base64 = base64.b64encode(image_data).decode("utf-8")

        resp = requests.post(
            "https://2captcha.com/in.php",
            data={"key": key, "method": "base64", "body": image_base64},
            timeout=30,
        )
        if resp.status_code == 200 and resp.text.strip().startswith("OK|"):
            task_id = resp.text.strip().split("|")[1]
            text = _poll_result(task_id, api_key)
            if text:
                _log(f"[캡챠 API] 해독 성공 (base64): {text}")
                return text
    except Exception as e:
        _log(f"[캡챠 API] base64 방식 실패: {e}")

    # 2) url 방식 폴백 (http/https URL인 경우)
    if not task_id and (captcha_image_url or "").startswith("http"):
        try:
            resp = requests.post(
                "https://2captcha.com/in.php",
                data={"key": key, "method": "url", "url": captcha_image_url},
                timeout=30,
            )
            if resp.status_code == 200 and resp.text.strip().startswith("OK|"):
                task_id = resp.text.strip().split("|")[1]
                text = _poll_result(task_id, api_key)
                if text:
                    _log(f"[캡챠 API] 해독 성공 (url): {text}")
                    return text
        except Exception as e:
            _log(f"[캡챠 API] url 방식 실패: {e}")

    return None


def _dismiss_alert_if_any(driver):
    """가입확인 등 알림창이 있으면 무시(닫기)"""
    try:
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(0.3)
    except Exception:
        pass


def _check_and_dismiss_realname_alert(driver):
    """
    실명확인 대화상자가 있으면 취소 클릭 후 True 반환(해당 카페 스킵).
    네이티브 alert 또는 HTML 모달(취소 버튼) 모두 처리.
    """
    _ensure_selenium()
    # 1) 네이티브 confirm/alert
    try:
        alert = driver.switch_to.alert
        text = (alert.text or "").strip()
        if "실명" in text or "실명확인" in text:
            alert.dismiss()
            time.sleep(0.3)
            return True
        alert.accept()
        time.sleep(0.3)
        return False
    except Exception:
        pass
    # 2) HTML 모달의 취소 버튼 (실명확인 문구 있을 때)
    try:
        body = (driver.find_element(By.TAG_NAME, "body").text or "") + (driver.page_source or "")
        if "실명 확인 회원만" in body or "실명확인 페이지로 이동" in body:
            for btn in driver.find_elements(By.XPATH, "//button[contains(.,'취소')] | //a[contains(.,'취소')] | //*[@role='button'][contains(.,'취소')]"):
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.3)
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _ensure_main_window(driver, main_handles):
    """메인 창으로 복귀. target window already closed 등 오류 시 복구."""
    try:
        handles = driver.window_handles
        if not handles:
            return False
        for h in handles:
            if h in main_handles:
                driver.switch_to.window(h)
                return True
        driver.switch_to.window(handles[0])
        return True
    except Exception:
        try:
            handles = driver.window_handles
            if handles:
                driver.switch_to.window(handles[0])
                return True
        except Exception:
            pass
        return False


def _close_popup_if_any(driver, main_handles):
    """팝업 창이 열려 있으면 닫고 메인 창으로 복귀. 알림창 먼저 닫기."""
    try:
        _dismiss_alert_if_any(driver)
        if len(driver.window_handles) <= len(main_handles):
            return _ensure_main_window(driver, main_handles)
        for h in list(driver.window_handles):
            if h not in main_handles:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                    _dismiss_alert_if_any(driver)
                except Exception:
                    pass
                break
        return _ensure_main_window(driver, main_handles)
    except Exception:
        return _ensure_main_window(driver, main_handles)


def _fill_join_questions(driver, idx, cafe_name, log, join_answer_text=None):
    """가입 질문 영역에 답변 입력 (posting_help 방식)"""
    _log = log or print
    _ensure_selenium()
    answer_text = (join_answer_text or "").strip() or "넵.알겠습니다."
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    def _is_join_page(d):
        try:
            if d.find_elements(By.CSS_SELECTOR, "#app .CafeJoin"):
                return True
            if d.find_elements(By.CSS_SELECTOR, ".join_qna_area, .join_info_grid, textarea.answer_textarea"):
                return True
            for elem in d.find_elements(By.CSS_SELECTOR, "h2.menu_name"):
                if elem and "카페 가입하기" in (elem.text or ""):
                    return True
            url = d.current_url or ""
            if "CafeJoin" in url or "/join" in url or "ca-fe" in url:
                return True
            return False
        except Exception:
            return False

    # 탭 전환 (가입 페이지 찾기)
    is_valid = _is_join_page(driver)
    if not is_valid and len(driver.window_handles) > 1:
        for h in driver.window_handles:
            try:
                driver.switch_to.window(h)
                time.sleep(0.5)
                if _is_join_page(driver):
                    is_valid = True
                    break
            except Exception:
                continue

    # iframe 전환 (탭에서 못 찾으면)
    if not is_valid:
        try:
            driver.switch_to.default_content()
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(0.5)
                    if _is_join_page(driver):
                        is_valid = True
                        break
                    driver.switch_to.default_content()
                except Exception:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
            if not is_valid:
                driver.switch_to.default_content()
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    if not is_valid:
        return

    time.sleep(3)  # 가입 폼 로딩 대기
    handled_any_qna = False

    # 1) join_qna_area 단위로 처리 (라디오/라벨 랜덤 + textarea 입력)
    try:
        qna_areas = driver.find_elements(By.CSS_SELECTOR, ".join_qna_area")
    except Exception:
        qna_areas = []

    if qna_areas:
        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 질문 영역 {len(qna_areas)}개 발견. 답변 처리 중...")
        for area_i, area in enumerate(qna_areas, 1):
            try:
                # (A) 라디오/라벨 중 랜덤 1개 선택
                radio_inputs = area.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                option_labels = area.find_elements(By.CSS_SELECTOR, "label.label")
                choose_from = []
                for el in option_labels:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            choose_from.append(el)
                    except Exception:
                        continue
                if not choose_from:
                    for el in radio_inputs:
                        try:
                            if el.is_displayed() and el.is_enabled():
                                choose_from.append(el)
                        except Exception:
                            continue
                if choose_from:
                    chosen = random.choice(choose_from)
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", chosen
                        )
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", chosen)
                        handled_any_qna = True
                        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 질문 영역 {area_i}: 선택형 답변 랜덤 선택 완료")
                    except Exception:
                        try:
                            chosen.click()
                            handled_any_qna = True
                        except Exception:
                            pass

                # (A-2) 체크박스 (동의 등) 선택
                for cb in area.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
                    try:
                        if cb.is_displayed() and cb.is_enabled() and not cb.is_selected():
                            driver.execute_script(
                                "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", cb
                            )
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", cb)
                            handled_any_qna = True
                    except Exception:
                        continue

                # (B) textarea 또는 input[type=text]가 있으면 입력
                for ta in area.find_elements(By.CSS_SELECTOR, "textarea.answer_textarea"):
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", ta
                        )
                        time.sleep(0.3)
                        ta.click()
                        time.sleep(0.2)
                        ta.clear()
                        ta.send_keys(answer_text)
                        ta.send_keys(Keys.TAB)
                        time.sleep(0.3)
                        handled_any_qna = True
                    except Exception:
                        continue
                for inp in area.find_elements(By.CSS_SELECTOR, "input.input_text[type='text']"):
                    try:
                        if inp.is_displayed() and inp.get_attribute("type") == "text":
                            driver.execute_script(
                                "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", inp
                            )
                            time.sleep(0.3)
                            inp.click()
                            time.sleep(0.2)
                            inp.clear()
                            inp.send_keys(answer_text)
                            inp.send_keys(Keys.TAB)
                            time.sleep(0.3)
                            handled_any_qna = True
                    except Exception:
                        continue
            except Exception as e:
                _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 질문 영역 {area_i} 처리 중 오류: {e}")

        time.sleep(1)

    # 2) fallback: textarea.answer_textarea, input.input_text 또는 join_info_grid 내 입력란
    try:
        if not handled_any_qna:
            answer_elements = []
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.answer_textarea"))
                )
                answer_elements = driver.find_elements(By.CSS_SELECTOR, "textarea.answer_textarea")
            except Exception:
                try:
                    question_textareas = []
                    question_num = 1
                    while True:
                        try:
                            elem = WebDriverWait(driver, 2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, f"#question_{question_num}"))
                            )
                            try:
                                ta = elem.find_element(By.CSS_SELECTOR, "textarea")
                                question_textareas.append(ta)
                            except Exception:
                                question_textareas.append(elem)
                            question_num += 1
                        except Exception:
                            break
                    if question_textareas:
                        answer_elements = question_textareas
                except Exception:
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((
                                By.XPATH,
                                "//div[contains(@class,'join_info_grid')][.//strong[contains(.,'가입질문')]]//textarea"
                            ))
                        )
                        answer_elements = driver.find_elements(
                            By.XPATH,
                            "//div[contains(@class,'join_info_grid')][.//strong[contains(.,'가입질문')]]//textarea"
                        )
                    except Exception:
                        pass
            if not answer_elements:
                try:
                    inps = driver.find_elements(By.XPATH, "//div[contains(@class,'join_info_grid')][.//strong[contains(.,'가입질문')]]//input[@type='text']")
                    if inps:
                        answer_elements = inps
                except Exception:
                    pass
            if not answer_elements:
                try:
                    for grid in driver.find_elements(By.CSS_SELECTOR, "div.join_info_grid"):
                        try:
                            name_el = grid.find_element(By.CSS_SELECTOR, "strong.name")
                            if name_el and "가입질문" in (name_el.text or ""):
                                for ta in grid.find_elements(By.TAG_NAME, "textarea"):
                                    if ta.is_displayed():
                                        answer_elements.append(ta)
                                for inp in grid.find_elements(By.CSS_SELECTOR, "input[type='text']"):
                                    if inp.is_displayed():
                                        answer_elements.append(inp)
                        except Exception:
                            continue
                except Exception:
                    pass

            if answer_elements:
                _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 질문 {len(answer_elements)}개 발견. 모두 답변 입력 중...")
                for i, elem in enumerate(answer_elements, 1):
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem
                        )
                        time.sleep(0.5)
                        elem.click()
                        time.sleep(0.3)
                        elem.clear()
                        elem.send_keys(answer_text)
                        elem.send_keys(Keys.TAB)
                        time.sleep(0.5)
                    except Exception as e:
                        _log(f"[도우미 가입] [{idx}] {cafe_name} - 질문 {i}/{len(answer_elements)} 답변 입력 중 오류: {e}")
                time.sleep(1)
    except Exception as e:
        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 질문 확인 중 오류: {e}")
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def _ensure_valid_window(driver):
    """닫힌 창 참조 시 복구: 유효한 창으로 전환."""
    try:
        handles = driver.window_handles
        if handles:
            driver.switch_to.window(handles[0])
            return True
    except Exception:
        pass
    return False


def _verify_write_access(driver, cafe_id, menu_id, log=None):
    """
    글쓰기 페이지로 이동 가능한지 검증.
    가입승인대기중 등이면 글쓰기 불가 → False.
    글쓰기 폼이 보이면 True.
    """
    _log = log or print
    if not cafe_id or not menu_id:
        return False
    try:
        write_url = (
            f"https://cafe.naver.com/ca-fe/cafes/{cafe_id}/menus/{menu_id}"
            f"/articles/write?boardType=L"
        )
        driver.get(write_url)
        time.sleep(3)

        body_text = (driver.find_element(By.TAG_NAME, "body").text or "") + (driver.page_source or "")
        # 글쓰기 불가 사유 (가입승인대기중, 가입 대기중 등)
        blocked = (
            "회원이 아닙니다", "회원이 아니", "가입해 주세요", "승인 대기", "가입승인대기", "승인 후 이용",
            "가입 대기중", "가입대기중", "가입 신청을 취소", "메니저가 승인"
        )
        if any(x in body_text for x in blocked):
            return False
        # 글쓰기 폼 확인 (제목 입력란 등)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.textarea_input, .se-section-text, .editor_body"))
            )
            return True
        except TimeoutException:
            return False
    except Exception as e:
        _log(f"[도우미 가입] 글쓰기 검증 실패: {e}")
        return False


def _try_join_one(driver, idx, cafe_name, cafe_url, cafe_id, menu_id, captcha_api_key, log, join_answer_text=None):
    """한 카페에 가입 시도. 성공 시 dict 반환, 실패 시 None."""
    _log = log or print
    _ensure_selenium()
    try:
        _ensure_valid_window(driver)
        _dismiss_alert_if_any(driver)
        _log(f"[도우미 가입] [{idx}] {cafe_name} - 이동 중: {cafe_url[:50]}...")
        driver.get(cafe_url)
        time.sleep(3)

        # 가입 버튼 찾기 (실명인증은 가입버튼 클릭 후 팝업 시에만 스킵)
        join_btn = None
        for sel in [
            "div.cafe-write-btn a._rosRestrict[onclick*='joinCafe']",
            "a._rosRestrict[onclick*='joinCafe']",
        ]:
            try:
                join_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except Exception:
                continue

        if not join_btn:
            try:
                write_btn = driver.find_element(By.CSS_SELECTOR, "div.cafe-write-btn a")
                onclick = write_btn.get_attribute("onclick") or ""
                if "writeBoard(" in onclick:
                    _log(f"[도우미 가입] [{idx}] {cafe_name} - 이미 멤버")
                    out_cid, out_mid = cafe_id, menu_id
                    try:
                        from cafe_extractor import extract_cafe_info, pick_best_menu_id
                        info = extract_cafe_info(cafe_url)
                        if info.get("cafe_id"):
                            out_cid = info["cafe_id"]
                            if info.get("menus"):
                                best = pick_best_menu_id(info["menus"], exclude_notice=True)
                                if best:
                                    out_mid = best
                    except Exception:
                        pass
                    return {"cafe_url": cafe_url, "cafe_id": out_cid, "menu_id": out_mid}
            except Exception:
                pass
            _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 버튼 없음")
            return None

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", join_btn
        )
        time.sleep(0.5)
        main_handles = set(driver.window_handles)
        join_btn.click()
        time.sleep(3)
        # 실명확인 대화상자(확인/취소)가 뜨면 취소 클릭 후 스킵
        if _check_and_dismiss_realname_alert(driver):
            _log(f"[도우미 가입] [{idx}] {cafe_name} - 실명확인 필요 카페, 취소 후 스킵")
            return None
        time.sleep(2)

        # 새 창이 열렸으면 해당 창으로 전환 (가입 팝업)
        try:
            WebDriverWait(driver, 5).until(lambda d: len(d.window_handles) > len(main_handles))
            for h in driver.window_handles:
                if h not in main_handles:
                    driver.switch_to.window(h)
                    _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 팝업 창으로 전환")
                    break
        except TimeoutException:
            pass  # 같은 창에서 모달로 표시되는 경우

        # 가입 질문 답변 (캡챠 전에 처리)
        _fill_join_questions(driver, idx, cafe_name, log, join_answer_text=join_answer_text)
        time.sleep(2)

        # 캡챠 처리 (최대 3회 재시도)
        captcha_success = False
        for retry in range(3):
            try:
                captcha_img = None
                captcha_selectors = [
                    "img.image[alt='캡차이미지']",
                    "img[alt*='캡차']",
                    "img[alt*='캡차이미지']",
                    "img.image[src*='captcha']",
                    "img[src*='captcha']",
                ]
                for sel in captcha_selectors:
                    try:
                        captcha_img = WebDriverWait(driver, 12).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                        if captcha_img and captcha_img.is_displayed():
                            break
                    except TimeoutException:
                        captcha_img = None
                        continue

                if not captcha_img:
                    try:
                        WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.join_info_grid"))
                        )
                        for area in driver.find_elements(By.CSS_SELECTOR, "div.join_info_grid"):
                            try:
                                name_elem = area.find_element(By.CSS_SELECTOR, "strong.name")
                                if name_elem and "보안절차" in (name_elem.text or ""):
                                    captcha_img = area.find_element(By.CSS_SELECTOR, "img.image[alt='캡차이미지']")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # iframe 내부에서 캡차 탐색 (가입 폼이 iframe에 있는 경우)
                if not captcha_img:
                    try:
                        driver.switch_to.default_content()
                        for iframe in driver.find_elements(By.CSS_SELECTOR, "iframe"):
                            try:
                                driver.switch_to.frame(iframe)
                                for sel in ["img.image[alt='캡차이미지']", "img[alt*='캡차']", "img[src*='captcha']"]:
                                    try:
                                        captcha_img = driver.find_element(By.CSS_SELECTOR, sel)
                                        if captcha_img and captcha_img.is_displayed():
                                            _log(f"[도우미 가입] [{idx}] {cafe_name} - iframe 내 캡차 발견")
                                            break
                                    except Exception:
                                        continue
                                if captcha_img:
                                    break
                                driver.switch_to.default_content()
                            except Exception:
                                try:
                                    driver.switch_to.default_content()
                                except Exception:
                                    pass
                    except Exception:
                        try:
                            driver.switch_to.default_content()
                        except Exception:
                            pass

                if not captcha_img:
                    if retry < 2:
                        time.sleep(3)  # 페이지 로딩 대기 후 재시도
                        continue
                    break

                captcha_url = captcha_img.get_attribute("src")
                if not captcha_url:
                    time.sleep(2)
                    continue

                if not captcha_api_key or not str(captcha_api_key).strip():
                    _log(f"[도우미 가입] [{idx}] {cafe_name} - 캡챠 발견, API 키 없음 (2captcha 키 입력 필요)")
                    return None

                _log(f"[도우미 가입] [{idx}] {cafe_name} - 캡챠 해독 시도 {retry + 1}/3")
                text = _solve_captcha(captcha_url, captcha_api_key, log)
                if not text:
                    time.sleep(2)
                    continue

                inp = None
                for inp_sel in ["input#captcha.input_text", "input#captcha", "input.input_text[name*='captcha']", "input[name='captcha']"]:
                    try:
                        inp = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, inp_sel))
                        )
                        break
                    except TimeoutException:
                        continue
                if not inp:
                    raise TimeoutException("캡차 입력란을 찾을 수 없음")
                inp.clear()
                inp.send_keys(text)
                time.sleep(1)
                confirm_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "div.join_btn a.BaseButton--skinGreen")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", confirm_btn)
                time.sleep(0.5)
                confirm_btn.click()
                time.sleep(3)

                captcha_failed = False
                try:
                    err_label = driver.find_element(By.CSS_SELECTOR, "label[for='captcha'].label_text")
                    if err_label and err_label.is_displayed():
                        t = (err_label.text or "").strip()
                        if "잘못 입력" in t or "자동 가입 방지" in t:
                            captcha_failed = True
                except Exception:
                    pass

                if captcha_failed:
                    try:
                        inp = driver.find_element(By.CSS_SELECTOR, "input#captcha.input_text")
                        inp.clear()
                    except Exception:
                        pass
                    time.sleep(1)
                    continue

                captcha_success = True
                _log(f"[도우미 가입] [{idx}] {cafe_name} - 캡챠 해독 및 가입 완료")
                # 가입확인 알림창 무시 후 팝업 닫고 메인 창 복귀
                time.sleep(1)
                _dismiss_alert_if_any(driver)
                _close_popup_if_any(driver, main_handles)
                break
            except TimeoutException:
                break
            except Exception as e:
                _log(f"[도우미 가입] [{idx}] {cafe_name} - 캡챠 처리 오류: {e}")
                if retry < 2:
                    time.sleep(2)
                else:
                    return None

        if not captcha_success:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            try:
                captcha_img = driver.find_element(By.CSS_SELECTOR, "img.image[alt='캡차이미지']")
                if captcha_img and captcha_img.is_displayed():
                    _log(f"[도우미 가입] [{idx}] {cafe_name} - 캡챠 해독 실패 (최대 재시도 초과)")
                    _close_popup_if_any(driver, main_handles)
                    return None
            except Exception:
                pass
            # 캡챠 없이 가입 질문만 있는 경우: 가입 확인 버튼 클릭
            clicked_confirm = False
            for btn_sel in [
                "div.join_btn a.BaseButton--skinGreen",
                "a.BaseButton--skinGreen",
                "button[type='submit']",
                "a[onclick*='join']",
                ".join_btn a",
            ]:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, btn_sel)
                    if btn and btn.is_displayed() and btn.is_enabled():
                        driver.execute_script(
                            "arguments[0].scrollIntoView({behavior:'smooth',block:'center'});", btn
                        )
                        time.sleep(0.5)
                        btn.click()
                        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 확인 버튼 클릭 (캡챠 없음)")
                        time.sleep(3)
                        clicked_confirm = True
                        break
                except Exception:
                    continue
            if not clicked_confirm:
                try:
                    driver.switch_to.default_content()
                    for ifr in driver.find_elements(By.CSS_SELECTOR, "iframe"):
                        try:
                            driver.switch_to.frame(ifr)
                            for sel in ["div.join_btn a", "a.BaseButton--skinGreen", "button[type='submit']"]:
                                try:
                                    b = driver.find_element(By.CSS_SELECTOR, sel)
                                    if b and b.is_displayed() and b.is_enabled():
                                        driver.execute_script("arguments[0].click();", b)
                                        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 확인 버튼 클릭 (iframe)")
                                        time.sleep(3)
                                        clicked_confirm = True
                                        break
                                except Exception:
                                    continue
                            driver.switch_to.default_content()
                            if clicked_confirm:
                                break
                        except Exception:
                            try:
                                driver.switch_to.default_content()
                            except Exception:
                                pass
                except Exception:
                    pass
            _close_popup_if_any(driver, main_handles)

        # 가입 완료 후 cafe_id, menu_id 추출 (로그인 상태 드라이버로 재추출 — requests는 비로그인이라 메뉴 미노출)
        out_cid = cafe_id
        out_mid = menu_id
        try:
            from cafe_extractor import extract_cafe_info, pick_best_menu_id
            _ensure_valid_window(driver)
            driver.get(cafe_url)
            time.sleep(2)
            member_html = driver.page_source or ""
            info = extract_cafe_info(cafe_url, html=member_html)
            if info.get("cafe_id") and info.get("menus"):
                out_cid = info["cafe_id"]
                best_mid = pick_best_menu_id(info["menus"], exclude_notice=True)
                if best_mid and best_mid != "0":
                    out_mid = best_mid
                    _log(f"[도우미 가입] [{idx}] {cafe_name} - 추출: cafe_id={out_cid}, menu_id={out_mid}")
        except Exception as ex:
            _log(f"[도우미 가입] [{idx}] {cafe_name} - ID 추출 실패 (기존값 사용): {ex}")

        _log(f"[도우미 가입] [{idx}] {cafe_name} - 가입 완료")
        return {"cafe_url": cafe_url, "cafe_id": out_cid, "menu_id": out_mid}
    except Exception as e:
        _log(f"[도우미 가입] [{idx}] {cafe_name} - 오류: {e}")
        return None


def run_helper_cafe_join(
    naver_id,
    naver_pw,
    helper_cafes,
    captcha_api_key,
    join_answer_text=None,
    log=None,
    stop_flag=None,
    driver_holder=None,
    on_progress=None,
    on_joined=None,
    agent_update_cb=None,
    accounts=None,
):
    """
    도우미 카페 리스트로 자동 가입 수행.

    Args:
        naver_id: 네이버 아이디 (accounts 없을 때 사용)
        naver_pw: 네이버 비밀번호 (accounts 없을 때 사용)
        helper_cafes: [{"cafe_url", "cafe_id", "menu_id"}, ...]
        captcha_api_key: 2captcha API 키
        join_answer_text: 가입 질문 기본 답변 (미입력 시 "넵.알겠습니다.")
        log: 로그 콜백
        stop_flag: 중지 여부 확인 함수 (callable, True 반환 시 중지)
        driver_holder: {"driver": ...} 드라이버 저장
        on_progress: (pct, text) 진행률 콜백
    # accounts: 다중아이디. 없으면 단일 계정으로 [{"id", "pw"}] 생성
    if accounts and len(accounts) > 0:
        acc_list = [{"id": (a.get("id") or "").strip(), "pw": (a.get("pw") or "").strip()} for a in accounts if (a.get("id") or "").strip() and (a.get("pw") or "").strip()]
    else:
        acc_list = [{"id": (naver_id or "").strip(), "pw": (naver_pw or "").strip()}] if (naver_id or "").strip() and (naver_pw or "").strip() else []
    if not acc_list:
        _log("[도우미 가입] 네이버 아이디/비밀번호 없음")
        return

        on_joined: (joined_list) 가입 완료 시 콜백
        accounts: [{"id", "pw"}, ...] 다중아이디 시 사용. 있으면 naver_id/naver_pw 무시.
    """
    _log = log or print
    driver_holder = driver_holder or {}
    stop_flag = stop_flag or (lambda: False)

    # accounts: 다중아이디. 없으면 단일 계정으로 [{"id", "pw"}] 생성
    if accounts and len(accounts) > 0:
        acc_list = [{"id": (a.get("id") or "").strip(), "pw": (a.get("pw") or "").strip()} for a in accounts if (a.get("id") or "").strip() and (a.get("pw") or "").strip()]
    else:
        acc_list = [{"id": (naver_id or "").strip(), "pw": (naver_pw or "").strip()}] if (naver_id or "").strip() and (naver_pw or "").strip() else []
    if not acc_list:
        _log("[도우미 가입] 네이버 아이디/비밀번호 없음")
        return

    from cafe_poster import setup_driver, login_to_naver, safe_quit_driver

    driver = driver_holder.get("driver")
    driver_owned_here = driver is None
    joined = []
    total = len(helper_cafes)
    last_acc_idx = -1

    try:
        if not driver:
            _log("[도우미 가입] 크롬 드라이버 설정 중...")
            driver = setup_driver(headless=False)
            driver_holder["driver"] = driver

            if stop_flag():
                return
            _log("[도우미 가입] 네이버 로그인 중...")
            acc = acc_list[0]
            if not login_to_naver(driver, acc["id"], acc["pw"], log=_log):
                _log("[도우미 가입] 로그인 실패")
                return
            last_acc_idx = 0
            time.sleep(2)

        for i, c in enumerate(helper_cafes):
            if stop_flag():
                _log("[도우미 가입] 중지됨")
                break
            pct = int((i / total) * 100)
            if on_progress:
                on_progress(pct, f"가입 중 ({i+1}/{total})")
            cafe_name = c.get("cafe_url", "")[:30] + "..."

            # 다중아이디: 해당 카페에 사용할 계정으로 전환
            acc_idx = i % len(acc_list)
            if acc_idx != last_acc_idx:
                acc = acc_list[acc_idx]
                _log(f"[도우미 가입] 계정 전환: {acc['id']} ({acc_idx+1}/{len(acc_list)})")
                if not login_to_naver(driver, acc["id"], acc["pw"], log=_log):
                    _log(f"[도우미 가입] 계정 {acc['id']} 로그인 실패, 스킵")
                    continue
                last_acc_idx = acc_idx
                time.sleep(2)

            try:
                _ensure_valid_window(driver)
            except Exception:
                pass
            result = _try_join_one(
                driver, i + 1, cafe_name,
                c.get("cafe_url", ""), c.get("cafe_id", ""), c.get("menu_id", ""),
                captcha_api_key, _log, join_answer_text=join_answer_text
            )
            r_url = c.get("cafe_url", "")
            if result:
                _ensure_valid_window(driver)
                _dismiss_alert_if_any(driver)
                r_url = result.get("cafe_url") or r_url
                r_cid = result.get("cafe_id") or ""
                r_mid = result.get("menu_id") or ""
                write_ok = _verify_write_access(driver, r_cid, r_mid, _log)
                if write_ok:
                    joined.append(result)
                    if agent_update_cb:
                        agent_update_cb(r_url, True, r_cid, r_mid, None)
                    else:
                        try:
                            from supabase_client import upsert_helper_cafe
                            if r_url and r_cid and r_mid:
                                upsert_helper_cafe(r_url, r_cid, r_mid, sort_order=i, log=_log)
                        except Exception as ex:
                            _log(f"[도우미 가입] helper_cafes 등록 실패: {ex}")
                else:
                    _log(f"[도우미 가입] [{i+1}] {cafe_name} - 가입승인대기중 등 글쓰기 불가, 리스트 제외 및 테이블에서 삭제")
                    if agent_update_cb:
                        agent_update_cb(r_url, False, None, None, "가입승인대기중")
                    else:
                        try:
                            from supabase_client import delete_helper_cafe_by_url
                            if r_url:
                                delete_helper_cafe_by_url(r_url, _log)
                        except Exception as ex:
                            _log(f"[도우미 가입] helper_cafes 삭제 실패: {ex}")
            else:
                if agent_update_cb:
                    agent_update_cb(r_url, False, None, None, "가입 실패")
            time.sleep(2)

        if on_progress:
            on_progress(100, "완료")
        if on_joined and joined:
            on_joined(joined)
        _log(f"[도우미 가입] 완료: {len(joined)}개 가입 성공")
    except Exception as e:
        _log(f"[도우미 가입] 오류: {e}")
    finally:
        if driver_owned_here and driver:
            safe_quit_driver(driver)
            driver_holder["driver"] = None


def _resolve_run_days(digits, year, month):
    """
    run_days 숫자(0~9)를 해당 월의 실제 실행일로 변환.
    0=10,20,30일 / 1=1,11,21일 / ... 2월은 29,30→28일(윤년 29일)
    구버전 [8,18,28] 등은 그대로 반환.
    """
    import calendar
    if not digits:
        return []
    # 구버전: 8, 18, 28 등 10 이상 포함 시 그대로 사용
    if any(isinstance(d, (int, float)) and d >= 10 for d in digits):
        return [int(d) for d in digits if isinstance(d, (int, float)) and 1 <= d <= 31]
    last_day = calendar.monthrange(year, month)[1]
    result = set()
    for d in digits:
        try:
            n = int(d)
        except (TypeError, ValueError):
            continue
        if n < 0 or n > 9:
            continue
        if n == 0:
            days = [10, 20, 30]
        else:
            days = [n, 10 + n, 20 + n]
        for day in days:
            result.add(min(day, last_day))  # 30일→2월 28/29, 29일→2월 28
    return sorted(result)


def run_cafe_join_job(
    owner_user_id,
    program_username,
    naver_id,
    naver_pw,
    captcha_api_key=None,
    stop_flag=None,
    log=None,
    on_progress=None,
    immediate=False,
    accounts=None,
    vm_name=None,
    target_count_override=None,
    driver_holder=None,
):
    """
    카페 자동가입 작업.
    - immediate=True: 날짜 체크 없이 즉시 실행
    - immediate=False: 오늘 날짜가 run_days에 포함될 때만 실행
    - post_tasks channel='cafe_autojoin'로 worker가 호출하거나, GUI에서 직접 호출 가능
    """
    from datetime import datetime
    from cafe_search import search_naver_cafes_selenium
    from cafe_extractor import extract_cafe_info, pick_best_menu_id, check_cafe_created_year, extract_cafe_created_year, check_no_recent_post
    from supabase_client import (
        fetch_cafe_join_policy,
        fetch_program_cafe_lists,
        insert_program_cafe_list,
    )

    _log = log or print
    stop_flag = stop_flag or (lambda: False)
    driver_holder = driver_holder if isinstance(driver_holder, dict) else {}
    driver_owned_here = not driver_holder.get("driver")

    try:
        policy = fetch_cafe_join_policy(log=_log)
        if not immediate:
            run_days_raw = policy.get("run_days") or [4, 14, 24]
            now = datetime.now()
            today = now.day
            year, month = now.year, now.month
            run_days = _resolve_run_days(run_days_raw, year, month)
            if today not in run_days:
                _log(f"[카페가입] 오늘({today}일)은 실행일이 아님 (선택={run_days_raw} → 해당일={run_days})")
                return False

        _DEFAULT_KEYWORDS = [
            "건강", "다이어트", "요리", "영화", "음악", "게임", "맛집", "여행", "부동산", "재테크",
            "육아", "반려동물", "뷰티", "패션", "운동", "독서", "취미", "인테리어", "자동차", "IT",
        ]
        raw = (policy.get("search_keyword") or "").strip()
        kw_list = [k.strip() for k in raw.split(",") if k.strip()] or _DEFAULT_KEYWORDS.copy()

        year_min = int(policy.get("created_year_min") or 2020)
        year_max = int(policy.get("created_year_max") or 2025)
        recent_days = int(policy.get("recent_post_days") or 7)
        recent_enabled = bool(policy.get("recent_post_enabled", True))
        target_count = int(target_count_override) if target_count_override is not None else int(policy.get("target_count") or 50)

        # accounts: 다중아이디. 없으면 단일 계정
        if accounts and len(accounts) > 0:
            acc_list = [{"id": (a.get("id") or "").strip(), "pw": (a.get("pw") or "").strip()} for a in accounts if (a.get("id") or "").strip() and (a.get("pw") or "").strip()]
        else:
            acc_list = [{"id": (naver_id or "").strip(), "pw": (naver_pw or "").strip()}] if (naver_id or "").strip() and (naver_pw or "").strip() else []
        if not acc_list:
            _log("[카페가입] 네이버 아이디/비밀번호 없음")
            return False
        cache_key = acc_list[0]["id"].strip()

        from cafe_poster import setup_driver, login_to_naver, safe_quit_driver, needs_naver_login
        driver = driver_holder.get("driver")
        had_driver = driver is not None
        if not driver:
            driver = setup_driver(headless=False)
            driver_holder["driver"] = driver

        # driver_holder에서 재사용 시: 이미 로그인되어 있으면 로그인 생략 (기존 창 유지)
        if had_driver and not needs_naver_login(driver):
            _log("[카페가입] ✔ 기존 브라우저 로그인 유지")
        else:
            if on_progress:
                on_progress(5, "네이버 로그인 중...")
            if not login_to_naver(driver, acc_list[0]["id"], acc_list[0]["pw"], log=_log):
                _log("[카페가입] 네이버 로그인 실패")
                return False
        last_acc_idx = 0
        time.sleep(2)

        # 기존 가입/저장된 카페 URL (중복 가입 방지)
        existing_urls = set()
        try:
            for acc in acc_list:
                nid = acc.get("id", "").strip()
                if nid:
                    existing = fetch_program_cafe_lists(naver_id=nid, statuses=["saved", "joined", "rejected"], use_service=True, log=_log)
                    for c in existing:
                        if c.get("cafe_url"):
                            existing_urls.add(c["cafe_url"])
        except Exception:
            pass

        # 최근 검색 결과 캐시 재사용 (다 쓸 때만 새 키워드로 검색)
        global _search_cache
        cache = _search_cache.get(cache_key) if cache_key else None
        urls_to_try = []
        if cache:
            candidates = [u for u in cache["urls"] if u not in cache["used"] and u not in existing_urls]
            if candidates:
                urls_to_try = candidates
                _log(f"[카페가입] 캐시 재사용: '{cache['keyword']}' 검색 결과 {len(candidates)}개 남음")
            else:
                cache = None
        if not urls_to_try:
            # 캐시 없음 또는 소진 → 새 키워드로 검색 (이전과 다른 키워드 선택)
            prev_kw = (cache.get("keyword") if isinstance(cache, dict) else None) or ""
            keyword = random.choice(kw_list)
            if len(kw_list) > 1:
                while keyword == prev_kw:
                    keyword = random.choice(kw_list)
            if on_progress:
                on_progress(10, "카페 검색 중...")
            urls = search_naver_cafes_selenium(
                driver, keyword, max_pages=200, stop_flag=stop_flag, log=_log
            )
            urls_reversed = list(reversed(urls))
            _log(f"[카페가입] 검색 결과 {len(urls)}개 카페 (키워드: {keyword})")
            _search_cache[cache_key] = {"urls": urls_reversed, "used": set(), "keyword": keyword}
            urls_to_try = [u for u in urls_reversed if u not in existing_urls]

        joined_count = 0
        total = len(urls_to_try)
        attempt_idx = 0  # 가입 시도 횟수 (다중아이디 교체용)

        # agent_cafe_lists에 등록하지 않을 reject_reason (가입대기중, 가입실패 등)
        _SKIP_INSERT_REASONS = ("가입대기중", "가입 대기중", "가입실패", "가입 실패")

        def _agent_cb(cafe_url, success, cafe_id, menu_id, reason, current_naver_id):
            if not success and reason and str(reason).strip() in _SKIP_INSERT_REASONS:
                _log(f"[카페가입] {reason} — agent_cafe_lists 미등록: {cafe_url[:50]}...")
                return
            status = "joined" if success else "rejected"
            insert_program_cafe_list(
                owner_user_id, program_username, cafe_url, cafe_id, menu_id,
                status=status, reject_reason=reason if not success else None,
                naver_id=current_naver_id, vm_name=vm_name, log=_log
            )

        for i, cafe_url in enumerate(urls_to_try):
            if stop_flag():
                _log("[카페가입] 중지됨")
                break
            if cafe_url in existing_urls:
                continue
            if joined_count >= target_count:
                _log(f"[카페가입] 목표 {target_count}개 달성")
                break

            if on_progress:
                pct = 15 + int((i / max(total, 1)) * 80)
                on_progress(pct, f"확인 및 가입 ({i+1}/{total}) - {cafe_url[:40]}...")

            try:
                # 드라이버로 카페 방문 → 렌더링된 HTML로 생성년도·정보 확인
                driver.get(cafe_url)
                time.sleep(2)
                main_html = driver.page_source

                info = extract_cafe_info(cafe_url, html=main_html)
                if info.get("error") or not info.get("cafe_id"):
                    if cache_key and cache_key in _search_cache:
                        _search_cache[cache_key]["used"].add(cafe_url)
                    continue
                cafe_id = info["cafe_id"]
                menus = info.get("menus") or []
                menu_id = pick_best_menu_id(menus, exclude_notice=True) or "0"

                year_ok = check_cafe_created_year(main_html, year_min, year_max)
                if year_ok is False:
                    detected_year = extract_cafe_created_year(main_html)
                    _log(f"[카페가입] 생성년도 불일치 스킵 (개설년도: {detected_year}, 허용: {year_min}~{year_max}): {cafe_url[:50]}...")
                    if cache_key and cache_key in _search_cache:
                        _search_cache[cache_key]["used"].add(cafe_url)
                    continue

                if recent_enabled:
                    # 전체글보기(메뉴0)로 이동 → tbody 내 td.type_date 날짜로 최근글 확인
                    art_urls = [
                        f"https://cafe.naver.com/f-e/cafes/{cafe_id}/menus/0",
                        f"https://cafe.naver.com/ArticleList.nhn?search.clubid={cafe_id}&search.menuid=0",
                    ]
                    art_html = ""
                    for au in art_urls:
                        try:
                            driver.get(au)
                            time.sleep(2)
                            art_html = driver.page_source
                            if art_html and ("tbody" in art_html or "type_date" in art_html or "board-list" in art_html):
                                break
                        except Exception:
                            continue
                    no_recent = check_no_recent_post(art_html or main_html, within_days=recent_days)
                    if no_recent is False:
                        _log(f"[카페가입] 최근글 있음 스킵 ({recent_days}일 이내): {cafe_url[:50]}...")
                        if cache_key and cache_key in _search_cache:
                            _search_cache[cache_key]["used"].add(cafe_url)
                        continue

                # 다중아이디: 해당 시도에 사용할 계정으로 전환
                acc_idx = attempt_idx % len(acc_list)
                if acc_idx != last_acc_idx:
                    acc = acc_list[acc_idx]
                    _log(f"[카페가입] 계정 전환: {acc['id']} ({acc_idx+1}/{len(acc_list)})")
                    if not login_to_naver(driver, acc["id"], acc["pw"], log=_log):
                        _log(f"[카페가입] 계정 {acc['id']} 로그인 실패, 스킵")
                        continue
                    last_acc_idx = acc_idx
                    time.sleep(2)
                attempt_idx += 1

                # 조건 통과 → 바로 가입 시도
                cafe_name = cafe_url[:40] + "..."
                result = _try_join_one(
                    driver, i + 1, cafe_name,
                    cafe_url, cafe_id, menu_id,
                    captcha_api_key, _log,
                )
                if result:
                    # 글쓰기 페이지 접근 검증: 가입 대기중이면 저장하지 않음
                    r_cid = result.get("cafe_id") or cafe_id
                    r_mid = result.get("menu_id") or menu_id
                    write_ok = _verify_write_access(driver, r_cid, r_mid, _log)
                    if write_ok:
                        joined_count += 1
                        existing_urls.add(cafe_url)
                        _agent_cb(cafe_url, True, r_cid, r_mid, None, acc_list[last_acc_idx]["id"])
                        _log(f"[카페가입] 가입 완료: {cafe_url[:50]}... ({joined_count}/{target_count})")
                    else:
                        _agent_cb(cafe_url, False, cafe_id, menu_id, "가입 대기중", acc_list[last_acc_idx]["id"])
                        _log(f"[카페가입] 가입 대기중 — 글쓰기 불가, 저장 안 함: {cafe_url[:50]}...")
                else:
                    _agent_cb(cafe_url, False, cafe_id, menu_id, "가입 실패", acc_list[last_acc_idx]["id"])
                # 처리한 카페는 캐시 used에 추가 (재시도 방지)
                if cache_key and cache_key in _search_cache:
                    _search_cache[cache_key]["used"].add(cafe_url)

            except Exception as ex:
                _log(f"[카페가입] 오류 {cafe_url[:40]}: {ex}")
            time.sleep(1)

        if on_progress:
            on_progress(100, "완료")
        _log(f"[카페가입] 작업 완료 (가입 {joined_count}개)")
        return True
    except Exception as e:
        _log(f"[카페가입] 오류: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver_owned_here:
            d = driver_holder.get("driver")
            if d:
                try:
                    safe_quit_driver(d)
                except Exception:
                    pass
                driver_holder["driver"] = None
