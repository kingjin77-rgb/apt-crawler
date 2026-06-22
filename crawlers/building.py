"""
국토교통부 건축HUB 건축물대장정보 크롤러
API: https://apis.data.go.kr/1613000/BldRgstHubService
총괄표제부 조회 — 건물 기본정보(용적률, 건폐율, 세대수, 구조, 층수 등)
"""
import os
import time
import json
import requests
from config import PUBLIC_DATA_API_KEY, REQUEST_DELAY

BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"

OPERATIONS = {
    "총괄표제부": "getBrRecapTitleInfo",
    "표제부": "getBrTitleInfo",
    "기본개요": "getBrBasisOulnInfo",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 서울 주요 구 시군구코드 + 대표 법정동코드
SEOUL_DISTRICTS = {
    "강남구": ("11680", "10300"),
    "서초구": ("11650", "10800"),
    "송파구": ("11710", "10100"),
    "강동구": ("11740", "10500"),
    "마포구": ("11440", "10200"),
    "영등포구": ("11560", "10500"),
    "용산구": ("11170", "10400"),
    "성동구": ("11200", "10600"),
    "동대문구": ("11230", "10100"),
    "성북구": ("11290", "10100"),
    "노원구": ("11350", "10100"),
    "은평구": ("11380", "10100"),
    "관악구": ("11620", "10200"),
    "구로구": ("11530", "10100"),
    "강북구": ("11305", "10100"),
    "강서구": ("11500", "10100"),
    "종로구": ("11110", "15400"),
    "중구": ("11140", "10100"),
    "동작구": ("11590", "10100"),
    "서대문구": ("11410", "10100"),
    "양천구": ("11470", "10200"),
    "광진구": ("11215", "10100"),
    "중랑구": ("11260", "10100"),
    "도봉구": ("11320", "10100"),
    "금천구": ("11545", "10100"),
}


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    return session


def _get_json(session: requests.Session, url: str, params: dict, retries: int = 2) -> dict | None:
    params["serviceKey"] = PUBLIC_DATA_API_KEY
    params["_type"] = "json"
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=20)
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


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def fetch_building_info(session: requests.Session, sigungu_cd: str, bjdong_cd: str,
                        operation: str = "getBrRecapTitleInfo",
                        page_no: int = 1, num_rows: int = 100) -> list[dict]:
    url = f"{BASE_URL}/{operation}"
    params = {
        "sigunguCd": sigungu_cd,
        "bjdongCd": bjdong_cd,
        "numOfRows": num_rows,
        "pageNo": page_no,
    }
    data = _get_json(session, url, params)
    if not data:
        return []

    try:
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})
        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            return []
        if isinstance(item_list, dict):
            item_list = [item_list]
        return item_list or []
    except Exception:
        return []


def parse_building_item(item: dict, gu_name: str = "") -> dict:
    bld_nm = item.get("bldNm", "") or ""
    plat_plc = item.get("platPlc", "") or ""
    new_plat_plc = item.get("newPlatPlc", "") or ""
    title = bld_nm if bld_nm else (new_plat_plc or plat_plc)
    if bld_nm and plat_plc:
        title = f"{bld_nm} ({plat_plc})"

    main_purps = item.get("mainPurpsCdNm", "") or ""
    grnd_flr = _safe_int(item.get("grndFlrCnt"))
    ugrnd_flr = _safe_int(item.get("ugrndFlrCnt"))
    floor_info = ""
    if grnd_flr:
        floor_info = f"지상{grnd_flr}층"
        if ugrnd_flr:
            floor_info += f"/지하{ugrnd_flr}층"

    content_parts = []
    if main_purps:
        content_parts.append(f"용도: {main_purps}")
    if floor_info:
        content_parts.append(f"층수: {floor_info}")
    vl_rat = _safe_float(item.get("vlRat"))
    if vl_rat:
        content_parts.append(f"용적률: {vl_rat}%")
    bc_rat = _safe_float(item.get("bcRat"))
    if bc_rat:
        content_parts.append(f"건폐율: {bc_rat}%")
    tot_area = _safe_float(item.get("totArea"))
    if tot_area:
        content_parts.append(f"연면적: {tot_area}㎡")
    hhld_cnt = _safe_int(item.get("hhldCnt"))
    if hhld_cnt:
        content_parts.append(f"세대수: {hhld_cnt}")
    use_apr_day = item.get("useAprDay", "") or ""
    if use_apr_day:
        content_parts.append(f"사용승인일: {use_apr_day}")

    return {
        "source": "건축물대장",
        "announce_id": str(item.get("mgmBldrgstPk", "")),
        "title": title[:500],
        "housing_type": "기타",
        "region_sido": "서울" if gu_name else "",
        "region_sigungu": gu_name,
        "region_address": new_plat_plc or plat_plc,
        "supply_count": hhld_cnt,
        "recruitment_start": "",
        "recruitment_end": "",
        "announce_date": use_apr_day[:10] if use_apr_day else "",
        "winner_date": "",
        "move_in_date": "",
        "min_price": None,
        "max_price": None,
        "url": "",
        "content": " | ".join(content_parts),
        "raw_data": json.dumps(item, ensure_ascii=False),
    }


def crawl_building(region_codes: dict[str, str]) -> list[dict]:
    results = []
    if not PUBLIC_DATA_API_KEY or PUBLIC_DATA_API_KEY == "YOUR_API_KEY_HERE":
        print("[건축물대장] API 키 미설정 — 건너뜀")
        return results

    session = _create_session()
    print("[건축물대장] 건축물대장 총괄표제부 수집 시작")

    region_names = set(region_codes.keys())
    if "서울" not in region_names and len(region_names) < 17:
        print("[건축물대장] 서울 미포함 — 건너뜀 (현재 서울 지역만 지원)")
        return results

    max_districts = int(os.getenv("BUILDING_MAX_DISTRICTS", "5"))
    max_pages = int(os.getenv("BUILDING_MAX_PAGES", "3"))
    district_count = 0

    for gu_name, (sigungu_cd, bjdong_cd) in SEOUL_DISTRICTS.items():
        if district_count >= max_districts:
            break

        print(f"  [{gu_name}] 조회 중...")
        for page in range(1, max_pages + 1):
            items = fetch_building_info(session, sigungu_cd, bjdong_cd, page_no=page)
            if not items:
                break
            for item in items:
                results.append(parse_building_item(item, gu_name))
            if len(items) < 100:
                break
            time.sleep(REQUEST_DELAY)

        district_count += 1
        time.sleep(REQUEST_DELAY)

    print(f"[건축물대장] {len(results)}건 수집")
    return results
