"""
청약홈 (applyhome.co.kr) 크롤러
- 아파트, 오피스텔, 도시형생활주택 분양공고 수집
- 공고문 전문 포함
"""
import time
import json
import re
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from config import REQUEST_DELAY

BASE_URL = "https://www.applyhome.co.kr"

# 분양 목록 API (청약홈 내부 Ajax)
LIST_API = "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListView.do"
DETAIL_API = "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetailView.do"

# 오피스텔/도시형
OFT_LIST_API = "https://www.applyhome.co.kr/ai/aib/selectRemndrLttotPblancListView.do"
OFT_DETAIL_API = "https://www.applyhome.co.kr/ai/aib/selectRemndrLttotPblancDetailView.do"

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
            print(f"  [재시도 {attempt+1}/{retries}] {url} → {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def _get(url: str, retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers={**_headers(), "Accept": "text/html"}, timeout=30)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"  [재시도 {attempt+1}/{retries}] {url} → {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def fetch_apt_list(region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    """아파트 분양공고 목록 수집"""
    payload = {
        "pageNo": page_no,
        "numOfRows": page_size,
        "sidoCode": region_code,
        "searchCondition": "",
    }
    data = _post(LIST_API, payload)
    if not data:
        return []

    items = data.get("dataBody", {}).get("data", {}).get("applyhomeAPTLttotPblancListVO", [])
    return items or []


def fetch_oft_list(region_code: str = "", page_no: int = 1, page_size: int = 100) -> list[dict]:
    """오피스텔/도시형생활주택 분양공고 목록 수집"""
    payload = {
        "pageNo": page_no,
        "numOfRows": page_size,
        "sidoCode": region_code,
    }
    data = _post(OFT_LIST_API, payload)
    if not data:
        return []
    items = data.get("dataBody", {}).get("data", {}).get("applyhomeRemndrLttotPblancListVO", [])
    return items or []


def fetch_apt_detail(pblanc_no: str, house_manage_no: str) -> dict | None:
    """아파트 공고 상세 + 공고문 전문"""
    payload = {
        "pblancNo": pblanc_no,
        "houseManageNo": house_manage_no,
    }
    data = _post(DETAIL_API, payload)
    if not data:
        return None
    return data.get("dataBody", {}).get("data", {})


def fetch_oft_detail(pblanc_no: str, house_manage_no: str) -> dict | None:
    """오피스텔 공고 상세"""
    payload = {
        "pblancNo": pblanc_no,
        "houseManageNo": house_manage_no,
    }
    data = _post(OFT_DETAIL_API, payload)
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
    """청약홈 아파트 항목 → 표준 딕셔너리"""
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
    """오피스텔/도시형 항목 → 표준 딕셔너리"""
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
    """상세 데이터에서 공고문 핵심 텍스트 추출"""
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
    """전국 전체 수집"""
    results = []

    print("[청약홈] 아파트 수집 시작")
    for region_name, region_code in region_codes.items():
        print(f"  → {region_name} ({region_code})")
        page = 1
        while True:
            items = fetch_apt_list(region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("pblancNo"):
                    detail = fetch_apt_detail(
                        item["pblancNo"], item.get("houseManageNo", "")
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
            items = fetch_oft_list(region_code, page_no=page)
            if not items:
                break
            for item in items:
                detail = None
                if fetch_detail and item.get("pblancNo"):
                    detail = fetch_oft_detail(
                        item["pblancNo"], item.get("houseManageNo", "")
                    )
                    time.sleep(REQUEST_DELAY)
                results.append(parse_oft_item(item, detail))
            if len(items) < 100:
                break
            page += 1
        time.sleep(REQUEST_DELAY)

    return results
