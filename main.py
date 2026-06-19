"""
전국 분양공고 자동 수집기
사용: python main.py [--regions 서울 경기] [--no-detail] [--export excel|csv|json|all]
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import DB_PATH, REGION_CODES, OUTPUT_DIR
from models.database import init_db, upsert_announcement
from crawlers.applyhome import crawl_all_regions as crawl_applyhome
from crawlers.lh import crawl_lh
from crawlers.sh import crawl_sh
from crawlers.public_data import crawl_public_data
from utils.exporter import export_excel, export_csv_by_region, export_json, print_summary
from utils.notion_exporter import export_notion


def parse_args():
    parser = argparse.ArgumentParser(description="전국 분양공고 자동 수집기")
    parser.add_argument(
        "--regions", nargs="*", default=None,
        help="수집할 시도 목록 (예: 서울 경기 부산). 미입력 시 전국"
    )
    parser.add_argument(
        "--sources", nargs="*", default=["applyhome", "lh", "sh", "public"],
        help="수집 출처 (applyhome lh sh public). 기본: 전체"
    )
    parser.add_argument(
        "--no-detail", action="store_true",
        help="공고문 전문 수집 생략 (빠른 목록만 수집)"
    )
    parser.add_argument(
        "--export", nargs="*", default=["excel"],
        choices=["excel", "csv", "json", "notion", "all"],
        help="내보내기 형식 (excel csv json notion all)"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="수집 현황 요약만 출력"
    )
    return parser.parse_args()


def run_crawl(args):
    region_filter = args.regions
    if region_filter:
        target_regions = {k: v for k, v in REGION_CODES.items() if k in region_filter}
        if not target_regions:
            print(f"[오류] 유효한 지역 없음: {region_filter}")
            print(f"사용 가능: {list(REGION_CODES.keys())}")
            sys.exit(1)
    else:
        target_regions = REGION_CODES

    fetch_detail = not args.no_detail
    sources = set(args.sources)

    print(f"\n수집 지역: {list(target_regions.keys())}")
    print(f"수집 출처: {sources}")
    print(f"공고문 전문: {'포함' if fetch_detail else '생략'}\n")

    engine = init_db(DB_PATH)
    total_new = 0
    total_updated = 0
    errors = []

    def save_items(items: list[dict]):
        nonlocal total_new, total_updated
        for item in items:
            is_new = upsert_announcement(engine, item)
            if is_new:
                total_new += 1
            else:
                total_updated += 1

    if "applyhome" in sources:
        try:
            items = crawl_applyhome(target_regions, fetch_detail=fetch_detail)
            save_items(items)
            print(f"  청약홈 수집: {len(items)}건")
        except Exception as e:
            errors.append(f"청약홈: {e}")
            print(f"  [청약홈 오류] {e}")

    if "lh" in sources:
        try:
            items = crawl_lh(target_regions, fetch_detail=fetch_detail)
            save_items(items)
            print(f"  LH 수집: {len(items)}건")
        except Exception as e:
            errors.append(f"LH: {e}")
            print(f"  [LH 오류] {e}")

    if "sh" in sources and ("서울" in target_regions or region_filter is None):
        try:
            items = crawl_sh(fetch_detail=fetch_detail)
            save_items(items)
            print(f"  SH 수집: {len(items)}건")
        except Exception as e:
            errors.append(f"SH: {e}")
            print(f"  [SH 오류] {e}")

    if "public" in sources:
        try:
            items = crawl_public_data(target_regions)
            save_items(items)
            print(f"  공공데이터포털 수집: {len(items)}건")
        except Exception as e:
            errors.append(f"공공데이터포털: {e}")
            print(f"  [공공데이터포털 오류] {e}")

    print(f"\n신규: {total_new}건 / 업데이트: {total_updated}건")

    if total_new == 0 and total_updated == 0:
        print("\n⚠️  모든 출처에서 수집 실패. 다음을 확인하세요:")
        print("  1. 한국 내 네트워크에서 실행 중인지 (해외/클라우드 IP 차단)")
        print("  2. 공공데이터포털 API 키 설정 (.env → PUBLIC_DATA_API_KEY)")
        print("  3. GitHub Actions 워크플로우로 자동 수집 설정")

    return engine


def run_export(engine, export_formats: list[str]):
    formats = set(export_formats)
    if "all" in formats:
        formats = {"excel", "csv", "json", "notion"}

    if "excel" in formats:
        export_excel(engine)
    if "csv" in formats:
        export_csv_by_region(engine)
    if "json" in formats:
        export_json(engine)
    if "notion" in formats:
        export_notion(engine)


def main():
    args = parse_args()
    engine = init_db(DB_PATH)

    if args.summary:
        print_summary(engine)
        return

    engine = run_crawl(args)
    print_summary(engine)

    if args.export:
        run_export(engine, args.export)


if __name__ == "__main__":
    main()
