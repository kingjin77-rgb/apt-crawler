"""
SH공사(서울주택도시공사) 크롤러
- https://www.i-sh.co.kr
- 서울시 공공임대/분양 공고
- Session 기반 요청으로 안정성 개선
"""
import time
import json
import requests
from bs4 import BeautifulSoup
from config import REQUEST_DELAY

BASE_URL = "https://www.i-sh.co.kr"
LIST_URL = f"{BASE_URL}/main/lay2/program/S1T294C295/web/announcement/list.do"
DETAIL_URL_PREFIX = f"{BASE_URL}/main/lay2/program/S1T294C295/web/announcement/view.do"

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
        "Referer": BASE_URL,
    })
    try:
        session.get(BASE_URL, timeout=5)
        time.sleep(1)
    except Exception as e:
        print(f"  [SH 세션 초기화 경고] {e}")
    return session


def fetch_sh_list(session: requests.Session, page_no: int = 1) -> list[dict]:
    params = {
        "pageIndex": page_no,
        "searchType": "",
        "searchValue": "",
    }
    try:
        resp = session.get(LIST_URL, params=params, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        items = []
        rows = soup.select("table tbody tr") or soup.select(".board-list li")

        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue

            link_tag = row.find("a", href=True)
            href = link_tag["href"] if link_tag else ""
            title = link_tag.get_text(strip=True) if link_tag else ""

            if not title:
                continue

            seq = ""
            if "seq=" in href:
                seq = href.split("seq=")[-1].split("&")[0]
            elif "idx=" in href:
                seq = href.split("idx=")[-1].split("&")[0]

            date_text = cols[-1].get_text(strip=True) if cols else ""

            items.append({
                "seq": seq,
                "title": title,
                "href": href if href.startswith("http") else BASE_URL + href,
                "date": date_text,
            })

        return items
    except Exception as e:
        print(f"  [SH 목록 오류] {e}")
        return []


def fetch_sh_detail(session: requests.Session, url: str) -> str:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        content_div = (
            soup.find("div", class_="board-view")
            or soup.find("div", class_="view-content")
            or soup.find("div", id="contents")
        )
        if content_div:
            return content_div.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)[:5000]
    except Exception as e:
        print(f"  [SH 상세 오류] {e}")
        return ""


def parse_sh_item(item: dict, content: str) -> dict:
    return {
        "source": "SH공사",
        "announce_id": item.get("seq", item.get("href", "")),
        "title": item.get("title", ""),
        "housing_type": _guess_type(item.get("title", "")),
        "region_sido": "서울",
        "region_sigungu": "",
        "region_address": "",
        "supply_count": None,
        "recruitment_start": "",
        "recruitment_end": "",
        "announce_date": item.get("date", ""),
        "winner_date": "",
        "move_in_date": "",
        "min_price": None,
        "max_price": None,
        "url": item.get("href", ""),
        "content": content,
        "raw_data": json.dumps(item, ensure_ascii=False),
    }


def _guess_type(title: str) -> str:
    if "오피스텔" in title:
        return "오피스텔"
    elif "도시형" in title:
        return "도시형생활주택"
    elif "임대" in title:
        return "공공임대"
    elif "분양" in title or "아파트" in title:
        return "아파트"
    return "SH공고"


def crawl_sh(fetch_detail: bool = True, max_pages: int = 10) -> list[dict]:
    results = []
    session = _create_session()
    print("[SH공사] 공고 수집 시작")

    for page in range(1, max_pages + 1):
        items = fetch_sh_list(session, page_no=page)
        if not items:
            break
        for item in items:
            content = ""
            if fetch_detail and item.get("href"):
                content = fetch_sh_detail(session, item["href"])
                time.sleep(REQUEST_DELAY)
            results.append(parse_sh_item(item, content))
        time.sleep(REQUEST_DELAY)

    return results
