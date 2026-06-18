import os
from dotenv import load_dotenv

load_dotenv()

# 공공데이터포털 API 키 (https://www.data.go.kr 에서 발급)
PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "YOUR_API_KEY_HERE")

# DB 경로
DB_PATH = os.getenv("DB_PATH", "data/apt_crawler.db")

# 수집 주기 (분)
CRAWL_INTERVAL_MINUTES = int(os.getenv("CRAWL_INTERVAL_MINUTES", "60"))

# 출력 디렉토리
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "data/output")

# 요청 딜레이 (초)
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.5"))

# Notion 연동
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# 지역 코드 (시도)
REGION_CODES = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "경기": "41",
    "강원": "42",
    "충북": "43",
    "충남": "44",
    "전북": "45",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}

# 분양 유형
HOUSING_TYPES = {
    "아파트": "APT",
    "오피스텔": "OFT",
    "도시형생활주택": "URB",
    "민간임대": "RHO",
    "공공임대": "PBL",
    "공공분양": "PBS",
}
