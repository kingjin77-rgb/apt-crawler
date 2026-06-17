---
title: 아파트 공고 수집기
emoji: 🏢
colorFrom: green
colorTo: teal
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
---

# 🏢 아파트 분양공고 자동 수집기 (Streamlit Web UI)

전국 아파트·오피스텔·도시형생활주택 등 모든 분양공고를 자동 수집합니다.

## 수집 출처
| 출처 | 유형 | 비고 |
|------|------|------|
| 청약홈 (applyhome.co.kr) | 아파트, 오피스텔, 도시형생활주택 | 공고문 전문 포함 |
| LH청약센터 (apply.lh.or.kr) | 공공임대, 공공분양 | |
| SH공사 (i-sh.co.kr) | 서울 공공임대/분양 | |
| 공공데이터포털 API | 아파트 청약공고 | API 키 필요 |

## 설치

```bash
pip install -r requirements.txt
```

## 설정

```bash
cp .env.example .env
# .env 편집 → PUBLIC_DATA_API_KEY 입력 (선택)
```

공공데이터포털 API 키: https://www.data.go.kr → 회원가입 → "주택청약" 검색 → 활용신청

## 사용법

### 1회 수집
```bash
# 전국 전체 수집 (공고문 전문 포함)
python main.py

# 특정 지역만
python main.py --regions 서울 경기 부산

# 공고문 전문 생략 (빠른 목록만)
python main.py --no-detail

# 특정 출처만
python main.py --sources applyhome lh

# CSV로 내보내기 (지역별 분리)
python main.py --export csv

# 모든 형식 내보내기
python main.py --export all
```

### 자동 스케줄러 (60분 주기)
```bash
python scheduler.py
```

### 현황 요약만 확인
```bash
python main.py --summary
```

## 출력 파일 구조

```
data/
├── apt_crawler.db          # SQLite DB (전체 데이터)
└── output/
    ├── 분양공고_20240612_100000.xlsx   # Excel (지역별 시트)
    ├── 서울_20240612_100000.csv
    ├── 경기_20240612_100000.csv
    └── 전국_20240612_100000.csv
```

## DB 스키마

| 컬럼 | 설명 |
|------|------|
| source | 출처 (청약홈/LH/SH 등) |
| announce_id | 원본 공고 ID |
| title | 공고명 |
| housing_type | 주택유형 |
| region_sido | 시도 |
| region_sigungu | 시군구 |
| region_address | 전체 주소 |
| supply_count | 공급세대수 |
| recruitment_start/end | 청약접수 기간 |
| announce_date | 공고일 |
| winner_date | 당첨자 발표일 |
| move_in_date | 입주예정일 |
| min_price / max_price | 분양가 (만원) |
| url | 공고문 URL |
| content | 공고문 전문 |
