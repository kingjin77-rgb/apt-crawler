"""
자동 수집 스케줄러
사용: python scheduler.py
"""
import sys
import os
import schedule
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config import CRAWL_INTERVAL_MINUTES, DB_PATH, REGION_CODES
from models.database import init_db, upsert_announcement
from crawlers.applyhome import crawl_all_regions as crawl_applyhome
from crawlers.lh import crawl_lh
from crawlers.sh import crawl_sh
from crawlers.public_data import crawl_public_data
from utils.exporter import export_excel, print_summary


def run_job():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 수집 시작")
    engine = init_db(DB_PATH)
    total_new = 0

    def save(items):
        nonlocal total_new
        for item in items:
            if upsert_announcement(engine, item):
                total_new += 1

    save(crawl_applyhome(REGION_CODES, fetch_detail=True))
    save(crawl_lh(REGION_CODES, fetch_detail=True))
    save(crawl_sh(fetch_detail=True))
    save(crawl_public_data(REGION_CODES))

    print(f"신규 공고: {total_new}건")
    if total_new > 0:
        export_excel(engine)
    print_summary(engine)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 완료\n")


if __name__ == "__main__":
    print(f"스케줄러 시작 — {CRAWL_INTERVAL_MINUTES}분 주기 수집")
    run_job()  # 즉시 1회 실행

    schedule.every(CRAWL_INTERVAL_MINUTES).minutes.do(run_job)

    while True:
        schedule.run_pending()
        time.sleep(30)
