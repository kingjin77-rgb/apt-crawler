"""
Notion 데이터베이스로 수집 데이터 내보내기
notion-client 패키지 필요: pip install notion-client
"""
import os
import re
from datetime import datetime
from notion_client import Client
from sqlalchemy.orm import Session
from models.database import Announcement


NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")


def _parse_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(\d{4})[-./]?(\d{2})[-./]?(\d{2})", date_str)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def _build_properties(item) -> dict:
    props = {
        "공고명": {"title": [{"text": {"content": item.title or "제목 없음"}}]},
        "공고 ID": {"rich_text": [{"text": {"content": str(item.announce_id or "")}}]},
    }

    if item.source:
        props["출처"] = {"select": {"name": item.source}}

    if item.housing_type:
        valid_types = ["아파트", "오피스텔", "도시형생활주택", "공공임대", "공공분양", "SH공고", "LH공고", "기타"]
        ht = item.housing_type if item.housing_type in valid_types else "기타"
        props["주택유형"] = {"select": {"name": ht}}

    if item.region_sido:
        valid_regions = ["서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        if item.region_sido in valid_regions:
            props["시도"] = {"select": {"name": item.region_sido}}

    if item.region_sigungu:
        props["시군구"] = {"rich_text": [{"text": {"content": str(item.region_sigungu)}}]}

    if item.region_address:
        props["주소"] = {"rich_text": [{"text": {"content": str(item.region_address)[:2000]}}]}

    if item.supply_count:
        props["공급세대수"] = {"number": item.supply_count}

    recruit_start = _parse_date(item.recruitment_start)
    if recruit_start:
        props["청약접수 시작"] = {"date": {"start": recruit_start}}

    recruit_end = _parse_date(item.recruitment_end)
    if recruit_end:
        props["청약접수 마감"] = {"date": {"start": recruit_end}}

    announce_date = _parse_date(item.announce_date)
    if announce_date:
        props["공고일"] = {"date": {"start": announce_date}}

    winner_date = _parse_date(item.winner_date)
    if winner_date:
        props["당첨자 발표일"] = {"date": {"start": winner_date}}

    if item.move_in_date:
        props["입주예정"] = {"rich_text": [{"text": {"content": str(item.move_in_date)}}]}

    if item.min_price:
        props["최저가(만원)"] = {"number": item.min_price}
    if item.max_price:
        props["최고가(만원)"] = {"number": item.max_price}

    if item.url:
        props["공고 URL"] = {"url": str(item.url)}

    if item.content:
        props["공고문 내용"] = {"rich_text": [{"text": {"content": str(item.content)[:2000]}}]}

    return props


def export_notion(engine, database_id: str = "", token: str = ""):
    db_id = database_id or NOTION_DATABASE_ID
    api_token = token or NOTION_TOKEN

    if not db_id or not api_token:
        print("[Notion] NOTION_TOKEN 또는 NOTION_DATABASE_ID 미설정 — 건너뜀")
        print("  .env에 다음을 추가하세요:")
        print("  NOTION_TOKEN=ntn_xxx (Notion Integration 토큰)")
        print("  NOTION_DATABASE_ID=xxx (데이터베이스 ID)")
        return 0

    notion = Client(auth=api_token)

    with Session(engine) as session:
        items = session.query(Announcement).all()

    if not items:
        print("[Notion] 내보낼 데이터 없음")
        return 0

    existing_ids = set()
    try:
        cursor = None
        while True:
            kwargs = {"database_id": db_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            resp = notion.databases.query(**kwargs)
            for page in resp.get("results", []):
                aid_prop = page.get("properties", {}).get("공고 ID", {})
                rt = aid_prop.get("rich_text", [])
                if rt:
                    existing_ids.add(rt[0].get("plain_text", ""))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
    except Exception as e:
        print(f"  [Notion 기존 데이터 조회 경고] {e}")

    created = 0
    for item in items:
        aid = str(item.announce_id or "")
        if aid in existing_ids:
            continue

        try:
            props = _build_properties(item)
            notion.pages.create(parent={"database_id": db_id}, properties=props)
            created += 1
        except Exception as e:
            print(f"  [Notion 저장 오류] {item.title}: {e}")

    print(f"[Notion] {created}건 신규 저장 (기존 {len(existing_ids)}건 스킵)")
    return created
