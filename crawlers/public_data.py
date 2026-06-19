"""
공공데이터포털 청약홈 분양정보 API 크롤러
- API: https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail
- 아파트 분양(청약) 공고 수집
- API 키 기반이라 해외/클라우드 IP에서도 동작
"""
import os
import time
import json
import requests
from config import PUBLIC_DATA_API_KEY, REQUEST_DELAY

# 청약홈 아파트 분양정보 상세조회 (공공데이터포털 ODcloud)
APT_API_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    return session


def _get_json(session: requests.Session, url: str, params: dict, retries: int = 2) -> dict | None:
    params["serviceKey"] = PUBLIC_DATA_API_KEY
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text}
        except Exception as e:
            print(f"  [재시도 {attempt+1}/{retries}] {e}")
            time.sleep(REQUEST_DELAY)
    return None


def fetch_apt_lttot(session: requests.Session, page_no: int = 1, per_page: int = 100) -> list[dict]:
    params = {
        "page": page_no,
        "perPage": per_page,
    }
    data = _get_json(session, APT_API_URL, params)
    if not data:
        return []
    return data.get("data", []) or []


def parse_public_apt_item(item: dict) -> dict:
    return {
        "source": "공공데이터포털",
        "announce_id": str(item.get("HOUSE_MANAGE_NO", item.get("PBLANC_NO", ""))),
        "title": item.get("HOUSE_NM", ""),
        "housing_type": item.get("HOUSE_SECD_NM", "아파트"),
        "region_sido": item.get("SUBSCRPT_AREA_CODE_NM", ""),
        "region_sigungu": "",
        "region_address": item.get("HSSPLY_ADRES", ""),
        "supply_count": _safe_int(item.get("TOT_SUPLY_HSHLDCO")),
        "recruitment_start": item.get("RCEPT_BGNDE", ""),
        "recruitment_end": item.get("RCEPT_ENDDE", ""),
        "announce_date": item.get("RCRIT_PBLANC_DE", ""),
        "winner_date": item.get("PRZWNER_PRESNATN_DE", ""),
        "move_in_date": item.get("MVN_PREARNGE_YM", ""),
        "min_price": None,
        "max_price": None,
        "url": item.get("PBLANC_URL", ""),
        "content": json.dumps(item, ensure_ascii=False),
        "raw_data": json.dumps(item, ensure_ascii=False),
    }


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def crawl_public_data(region_codes: dict[str, str]) -> list[dict]:
    results = []
    if not PUBLIC_DATA_API_KEY or PUBLIC_DATA_API_KEY == "YOUR_API_KEY_HERE":
        print("[공공데이터포털] API 키 미설정 — 건너뜀 (.env에 PUBLIC_DATA_API_KEY 설정 필요)")
        return results

    session = _create_session()
    print("[공공데이터포털] 아파트 청약공고 수집 시작")

    # 전국(17개 시도) 요청이면 지역 필터 없이 전체 수집
    region_names = set(region_codes.keys())
    collect_all = len(region_names) >= 17

    page = 1
    # 최신 분양공고 위주로 수집 (역대 전체 수집 시 Notion 내보내기 과부하)
    max_pages = int(os.getenv("PUBLIC_MAX_PAGES", "5"))
    while page <= max_pages:
        items = fetch_apt_lttot(session, page_no=page, per_page=100)
        if not items:
            break
        for item in items:
            sido = item.get("SUBSCRPT_AREA_CODE_NM", "")
            if not collect_all and not any(r in sido for r in region_names):
                continue
            results.append(parse_public_apt_item(item))
        if len(items) < 100:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    print(f"[공공데이터포털] {len(results)}건 수집")
    return results
