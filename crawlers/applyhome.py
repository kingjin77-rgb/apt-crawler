"""
청약홈 (applyhome.co.kr) 크롤러
- 아파트, 오피스텔, 도시형생활주택 분양공고 수집
- 공고문 전문 포함
- Session 기반 요청으로 안정성 개선
"""
import time
import json
import re
import requests
from config import REQUEST_DELAY

BASE_URL = "https://www.applyhome.co.kr"

LIST_API = f"{BASE_URL}/ai/aia/selectAPTLttotPblancListView.do"
DETAIL_API = f"{BASE_URL}/ai/aia/selectAPTLttotPblancDetailView.do"

OFT_LIST_API = f"{BASE_URL}/ai/aib/selectRemndrLttotPblancListView.do"
OFT_DETAIL_API = f"{BASE_URL}/ai/aib/selectRemndrLttotPblancDetailView.do"

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
        session.get(BASE_URL, timeout=15)
        time.sleep(1)
    except Exception as e:
        print(f"  [세션 초기화 경고] {e}")
    return session


def _api_headers():
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/co/coa/selectMainView.do",
        "Origin": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def _post(session: requests.Session, url: str, payload: dict, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            resp = session.post(url, data=payload, headers=_api_headers(), timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [재시도 {attempt+1}/{retries}] {url} → {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def fetch_apt_list(session: requests.Session, region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    payload = {
        "pageNo": page_no,
        "numOfRows": page_size,
        "sidoCode": region_code,
        "searchCondition": "",
    }
    data = _post(session, LIST_API, payload)
    if not data:
        return []
    items = data.get("dataBody", {}).get("data", {}).get("applyhomeAPTLttotPblancListVO", [])
    return items or []


def fetch_oft_list(session: requests.Session, region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    payload = {
        "pageNo": page_no,
        "numOfRows": page_size,
        "sidoCode": region_code,
    }
    data = _post(session, OFT_LIST_API, payload)
    if not data:
        return []
    items = data.get("dataBody", {}).get("data", {}).get("applyhomeRemndrLttotPblancListVO", [])
    return items or []


def fetch_apt_detail(session: requests.Session, pblanc_no: str, house_manage_no: str) -> dict | None:
    payload = {
        "pblancNo": pblanc_no,
        "houseManageNo": house_manage_no,
    }
    data = _post(session, DETAIL_API, payload)
    if not data:
        return None
    return data.get("dataBody", {}).get("data", {})


def fetch_oft_detail(session: requests.Session, pblanc_no: str, house_manage_no: str) -> dict | None:
    payload = {
        "pblancNo": pblanc_no,
        "houseManageNo": house_manage_no,
    }
    data = _post(session, OFT_DETAIL_API, payload)
    if not data:
        return None
    return data.get("dataBody", {}).get("data", {})


def _extract_price(text: str | None) -> int | None:
    if not text:
        return None
    nums = re.findall(r"[\d,]+", str(text))
    if nums:
        return int(nums[0].replace(",", ""))
    return None


def parse_apt_item(item: dict, detail: dict | None) -> dict:
    d = detail or {}
    house_info = d.get("applyhomeAPTLttotPblancDetailVO", item)
    supply_list = d.get("applyhomeAPTSuplyTypeDtlListVO", [])

    total_supply = sum(
        int(s.get("suplyHshldco", 0) or 0) for s in supply_list
    ) if supply_list else int(item.get("totSuplyHshldco", 0) or 0)

    prices = [
        int(s.get("lttotTopAmount", 0) or 0)
        for s in supply_list
        if s.get("lttotTopAmount")
    ]

    address = " ".join(filter(None, [
        house_info.get("bsnsMbyNm", ""),
        house_info.get("hssplyAdres", ""),
    ]))

    return {
        "source": "청약홈",
        "announce_id": str(item.get("pblancNo", "")),
        "title": item.get("houseNm", ""),
        "housing_type": item.get("houseSecd", "아파트"),
        "region_sido": item.get("sidoNm", ""),
        "region_sigungu": item.get("signguNm", ""),
        "region_address": address,
        "supply_count": total_supply,
        "recruitment_start": item.get("rceptBgnde", ""),
        "recruitment_end": item.get("rceptEndde", ""),
        "announce_date": item.get("pblancDe", ""),
        "winner_date": item.get("przwnerPresnatnDe", ""),
        "move_in_date": house_info.get("mvnPrearngeYm", ""),
        "min_price": min(prices) if prices else None,
        "max_price": max(prices) if prices else None,
        "url": f"{BASE_URL}/ai/aia/selectAPTLttotPblancDetailView.do?pblancNo={item.get('pblancNo')}&houseManageNo={item.get('houseManageNo')}",
        "content": _extract_content(d),
        "raw_data": json.dumps(d, ensure_ascii=False),
    }


def parse_oft_item(item: dict, detail: dict | None) -> dict:
    d = detail or {}
    house_info = d.get("applyhomeRemndrLttotPblancDetailVO", item)

    address = " ".join(filter(None, [
        house_info.get("bsnsMbyNm", ""),
        house_info.get("hssplyAdres", ""),
    ]))

    housing_type = item.get("houseSecd", "")
    if "오피스텔" in housing_type or housing_type == "OFT":
        housing_type = "오피스텔"
    elif "도시형" in housing_type:
        housing_type = "도시형생활주택"
    else:
        housing_type = housing_type or "기타"

    return {
        "source": "청약홈",
        "announce_id": f"OFT_{item.get('pblancNo', '')}",
        "title": item.get("houseNm", ""),
        "housing_type": housing_type,
        "region_sido": item.get("sidoNm", ""),
        "region_sigungu": item.get("signguNm", ""),
        "region_address": address,
        "supply_count": int(item.get("totSuplyHshldco", 0) or 0),
        "recruitment_start": item.get("rceptBgnde", ""),
        "recruitment_end": item.get("rceptEndde", ""),
        "announce_date": item.get("pblancDe", ""),
        "winner_date": item.get("przwnerPresnatnDe", ""),
        "move_in_date": house_info.get("mvnPrearngeYm", ""),
        "min_price": None,
        "max_price": None,
        "url": f"{BASE_URL}/ai/aib/selectRemndrLttotPblancDetailView.do?pblancNo={item.get('pblancNo')}&houseManageNo={item.get('houseManageNo')}",
        "content": _extract_content(d),
        "raw_data": json.dumps(d, ensure_ascii=False),
    }


def _extract_content(detail: dict) -> str:
    parts = []

    for key in ["applyhomeAPTLttotPblancDetailVO", "applyhomeRemndrLttotPblancDetailVO"]:
        info = detail.get(key, {})
        if info:
            parts.append("=== 공고 기본정보 ===")
            for k, v in info.items():
                if v and str(v).strip():
                    parts.append(f"{k}: {v}")

    supply_list = detail.get("applyhomeAPTSuplyTypeDtlListVO", [])
    if supply_list:
        parts.append("\n=== 공급유형별 상세 ===")
        for s in supply_list:
            parts.append(str(s))

    schedule_list = detail.get("applyhomeAPTRcptSheduleListVO", [])
    if schedule_list:
        parts.append("\n=== 청약일정 ===")
        for s in schedule_list:
            parts.append(str(s))

    return "\n".join(parts)


def crawl_all_regions(region_codes: dict[str, str], fetch_detail: bool = True) -> list[dict]:
    results = []
    session = _create_session()

    print("[청약홈] 아파트 수집 시작")
    for region_name, region_code in region_codes.items():
        print(f"  → {region_name} ({region_code})")
        page = 1
        while True:
            items = fetch_apt_list(session, region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("pblancNo"):
                    detail = fetch_apt_detail(
                        session, item["pblancNo"], item.get("houseManageNo", "")
                    )
                    time.sleep(REQUEST_DELAY)
                results.append(parse_apt_item(item, detail))
            if len(items) < 100:
                break
            page += 1
        time.sleep(REQUEST_DELAY)

    print("[청약홈] 오피스텔/도시형 수집 시작")
    for region_name, region_code in region_codes.items():
        print(f"  → {region_name} ({region_code})")
        page = 1
        while True:
            items = fetch_oft_list(session, region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("pblancNo"):
                    detail = fetch_oft_detail(
                        session, item["pblancNo"], item.get("houseManageNo", "")
                    )
                    time.sleep(REQUEST_DELAY)
                results.append(parse_oft_item(item, detail))
            if len(items) < 100:
                break
            page += 1
        time.sleep(REQUEST_DELAY)

    return results
