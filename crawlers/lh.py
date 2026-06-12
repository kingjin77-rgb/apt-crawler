"""
LH(한국토지주택공사) 청약센터 크롤러
- https://apply.lh.or.kr
- 공공임대 + 공공분양 공고 수집
"""
import time
import json
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from config import REQUEST_DELAY

BASE_URL = "https://apply.lh.or.kr"

# LH 내부 API
LIST_API = "https://apply.lh.or.kr/lhapply/apply/wt/wtmlttot/selectWtmLttotList.do"
DETAIL_API = "https://apply.lh.or.kr/lhapply/apply/wt/wtmlttot/selectWtmLttotDetail.do"

ua = UserAgent()


def _headers():
    return {
        "User-Agent": ua.random,
        "Referer": BASE_URL,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }


def _post(url: str, payload: dict, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            resp = requests.post(url, data=payload, headers=_headers(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [LH 재시도 {attempt+1}/{retries}] {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def fetch_lh_list(region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    """LH 공고 목록"""
    payload = {
        "pageIndex": page_no,
        "recordCountPerPage": page_size,
        "sido": region_code,
        "lttotType": "",       # 전체 유형
        "searchType": "",
        "searchValue": "",
    }
    data = _post(LIST_API, payload)
    if not data:
        return []
    return data.get("resultList", []) or []


def fetch_lh_detail(announce_id: str) -> dict | None:
    """LH 공고 상세"""
    payload = {"lttotId": announce_id}
    data = _post(DETAIL_API, payload)
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
    """LH 전국 수집"""
    results = []
    print("[LH청약센터] 공고 수집 시작")

    for region_name, region_code in region_codes.items():
        print(f"  → {region_name}")
        page = 1
        while True:
            items = fetch_lh_list(region_code=region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("lttotId"):
                    detail = fetch_lh_detail(item["lttotId"])
                    time.sleep(REQUEST_DELAY)
                results.append(parse_lh_item(item, detail))
            if len(items) < 100:
                break
            page += 1
        time.sleep(REQUEST_DELAY)

    return results
