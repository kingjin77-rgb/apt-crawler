"""
한국부동산원 청약홈 — 오피스텔·도시형·민간임대·생활숙박시설 분양정보 크롤러
API: https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getUrbtyOfctlLttotPblancDetail
API 키 기반 (ODcloud) — 해외/클라우드 IP에서도 동작
"""
import os
import time
import json
import requests
from config import PUBLIC_DATA_API_KEY, REQUEST_DELAY

OFCTL_API_URL = (
    "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/"
    "getUrbtyOfctlLttotPblancDetail"
)

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


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _detect_housing_type(item: dict) -> str:
    name = item.get("HOUSE_SECD_NM", "") or ""
    if "오피스텔" in name:
        return "오피스텔"
    if "도시형" in name:
        return "도시형생활주택"
    if "민간임대" in name or "임대" in name:
        return "기타"
    if "생활숙박" in name:
        return "기타"
    return name or "기타"


def parse_officetel_item(item: dict) -> dict:
    return {
        "source": "공공데이터포털",
        "announce_id": str(item.get("HOUSE_MANAGE_NO", item.get("PBLANC_NO", ""))),
        "title": item.get("HOUSE_NM", ""),
        "housing_type": _detect_housing_type(item),
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


def crawl_officetel(region_codes: dict[str, str]) -> list[dict]:
    results = []
    if not PUBLIC_DATA_API_KEY or PUBLIC_DATA_API_KEY == "YOUR_API_KEY_HERE":
        print("[오피스텔·도시형] API 키 미설정 — 건너뜀")
        return results

    session = _create_session()
    print("[오피스텔·도시형] 청약홈 오피스텔/도시형/민간임대/생활숙박시설 수집 시작")

    region_names = set(region_codes.keys())
    collect_all = len(region_names) >= 17

    page = 1
    max_pages = int(os.getenv("PUBLIC_MAX_PAGES", "5"))
    while page <= max_pages:
        params = {"page": page, "perPage": 100}
        data = _get_json(session, OFCTL_API_URL, params)
        if not data:
            break
        items = data.get("data", []) or []
        if not items:
            break
        for item in items:
            sido = item.get("SUBSCRPT_AREA_CODE_NM", "")
            if not collect_all and not any(r in sido for r in region_names):
                continue
            results.append(parse_officetel_item(item))
        if len(items) < 100:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    print(f"[오피스텔·도시형] {len(results)}건 수집")
    return results
