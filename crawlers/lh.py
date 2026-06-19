"""
LH(한국토지주택공사) 청약센터 크롤러
- https://apply.lh.or.kr
- 공공임대 + 공공분양 공고 수집
- Session 기반 요청으로 안정성 개선
"""
import time
import json
import requests
from config import REQUEST_DELAY

BASE_URL = "https://apply.lh.or.kr"

LIST_API = f"{BASE_URL}/lhapply/apply/wt/wtmlttot/selectWtmLttotList.do"
DETAIL_API = f"{BASE_URL}/lhapply/apply/wt/wtmlttot/selectWtmLttotDetail.do"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    try:
        session.get(BASE_URL, timeout=5)
        time.sleep(1)
    except Exception as e:
        print(f"  [LH 세션 초기화 경고] {e}")
    return session


def _api_headers():
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/lhapply/apply/wt/wtmlttot/selectWtmLttotListView.do",
        "Origin": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def _post(session: requests.Session, url: str, payload: dict, retries: int = 2) -> dict | None:
    for attempt in range(retries):
        try:
            resp = session.post(url, data=payload, headers=_api_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [LH 재시도 {attempt+1}/{retries}] {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def fetch_lh_list(session: requests.Session, region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    payload = {
        "pageIndex": page_no,
        "recordCountPerPage": page_size,
        "sido": region_code,
        "lttotType": "",
        "searchType": "",
        "searchValue": "",
    }
    data = _post(session, LIST_API, payload)
    if not data:
        return []
    return data.get("resultList", []) or []


def fetch_lh_detail(session: requests.Session, announce_id: str) -> dict | None:
    payload = {"lttotId": announce_id}
    data = _post(session, DETAIL_API, payload)
    if not data:
        return None
    return data.get("resultDetail", {})


def parse_lh_item(item: dict, detail: dict | None) -> dict:
    d = detail or {}

    housing_type = item.get("lttotType", "") or item.get("houseType", "")
    if "임대" in housing_type:
        housing_type = "공공임대"
    elif "분양" in housing_type:
        housing_type = "공공분양"
    else:
        housing_type = housing_type or "LH공고"

    announce_id = str(item.get("lttotId", item.get("id", "")))

    address_parts = [
        item.get("sidoNm", ""),
        item.get("signguNm", ""),
        item.get("adres", ""),
    ]
    address = " ".join(filter(None, address_parts))

    return {
        "source": "LH청약센터",
        "announce_id": announce_id,
        "title": item.get("houseNm", item.get("lttotNm", "")),
        "housing_type": housing_type,
        "region_sido": item.get("sidoNm", ""),
        "region_sigungu": item.get("signguNm", ""),
        "region_address": address,
        "supply_count": _safe_int(item.get("supplyHshldco")),
        "recruitment_start": item.get("rceptBgnde", ""),
        "recruitment_end": item.get("rceptEndde", ""),
        "announce_date": item.get("pblancDe", ""),
        "winner_date": item.get("przwnerPresnatnDe", ""),
        "move_in_date": item.get("mvnPrearngeYm", ""),
        "min_price": None,
        "max_price": None,
        "url": f"{BASE_URL}/lhapply/apply/wt/wtmlttot/selectWtmLttotDetail.do?lttotId={announce_id}",
        "content": json.dumps(d, ensure_ascii=False) if d else json.dumps(item, ensure_ascii=False),
        "raw_data": json.dumps({**item, **(d or {})}, ensure_ascii=False),
    }


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def crawl_lh(region_codes: dict[str, str], fetch_detail: bool = True) -> list[dict]:
    results = []
    session = _create_session()
    print("[LH청약센터] 공고 수집 시작")

    for region_name, region_code in region_codes.items():
        print(f"  → {region_name}")
        page = 1
        while True:
            items = fetch_lh_list(session, region_code=region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("lttotId"):
                    detail = fetch_lh_detail(session, item["lttotId"])
                    time.sleep(REQUEST_DELAY)
                results.append(parse_lh_item(item, detail))
            if len(items) < 100:
                break
            page += 1
        time.sleep(REQUEST_DELAY)

    return results
