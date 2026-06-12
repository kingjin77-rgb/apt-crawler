"""
공공데이터포털 국토교통부 주택청약 API 크롤러
- API: https://www.data.go.kr/data/15059466/openapi.do
- 청약공고 + 분양정보 수집
"""
import time
import json
import requests
from config import PUBLIC_DATA_API_KEY, REQUEST_DELAY

# 국토교통부 청약공고 API
APT_API_URL = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptLttot"
# 청약홈 공공 API (한국부동산원)
APPLY_API_BASE = "https://api.applyhome.co.kr"

# 공공데이터포털 주택분양보증 API
HUG_API_URL = "http://apis.data.go.kr/1611000/nsdi/LHBunayang/getLHBunayangList"


def _get_json(url: str, params: dict, retries: int = 3) -> dict | None:
    params["serviceKey"] = PUBLIC_DATA_API_KEY
    params.setdefault("_type", "json")
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text}
        except Exception as e:
            print(f"  [재시도 {attempt+1}/{retries}] {e}")
            time.sleep(REQUEST_DELAY * (attempt + 1))
    return None


def fetch_apt_lttot(sido_code: str = "", page_no: int = 1, num_of_rows: int = 100) -> list[dict]:
    """국토교통부 아파트 청약공고 API"""
    params = {
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "SIDO_CD": sido_code,
    }
    data = _get_json(APT_API_URL, params)
    if not data:
        return []

    try:
        items = data["response"]["body"]["items"]["item"]
        if isinstance(items, dict):
            items = [items]
        return items
    except (KeyError, TypeError):
        return []


def parse_public_apt_item(item: dict) -> dict:
    """공공데이터포털 아파트 항목 → 표준 딕셔너리"""
    return {
        "source": "공공데이터포털",
        "announce_id": str(item.get("HOUSE_MANAGE_NO", item.get("PBLANC_NO", ""))),
        "title": item.get("HOUSE_NM", ""),
        "housing_type": item.get("HOUSE_SECD_NM", "아파트"),
        "region_sido": item.get("SIDO_NM", ""),
        "region_sigungu": item.get("SIGNGU_NM", ""),
        "region_address": item.get("HSSPLY_ADRES", ""),
        "supply_count": _safe_int(item.get("TOT_SUPLY_HSHLDCO")),
        "recruitment_start": item.get("RCEPT_BGNDE", ""),
        "recruitment_end": item.get("RCEPT_ENDDE", ""),
        "announce_date": item.get("PBLANC_DE", ""),
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
    """공공데이터포털 전국 수집"""
    results = []
    if PUBLIC_DATA_API_KEY == "YOUR_API_KEY_HERE":
        print("[공공데이터포털] API 키 미설정 — 건너뜀 (.env에 PUBLIC_DATA_API_KEY 설정 필요)")
        return results

    print("[공공데이터포털] 아파트 청약공고 수집 시작")
    for region_name, region_code in region_codes.items():
        print(f"  → {region_name}")
        page = 1
        while True:
            items = fetch_apt_lttot(sido_code=region_code, page_no=page)
            if not items:
                break
            for item in items:
                results.append(parse_public_apt_item(item))
            if len(items) < 100:
                break
            page += 1
            time.sleep(REQUEST_DELAY)

    return results
