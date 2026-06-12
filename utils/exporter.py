"""
수집 데이터 내보내기 (Excel, CSV, JSON)
지역별 분리 시트/파일 지원
"""
import os
import json
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from models.database import Announcement, get_engine
from config import DB_PATH, OUTPUT_DIR


def load_all(engine) -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.query(Announcement).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            c.name: getattr(r, c.name)
            for c in Announcement.__table__.columns
        } for r in rows])


def export_excel(engine, output_dir: str = OUTPUT_DIR):
    """지역별 시트로 Excel 내보내기"""
    os.makedirs(output_dir, exist_ok=True)
    df = load_all(engine)
    if df.empty:
        print("데이터 없음.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"분양공고_{timestamp}.xlsx")

    drop_cols = ["id", "raw_data"]
    df_out = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # 전체
        df_out.to_excel(writer, sheet_name="전체", index=False)

        # 지역별 시트
        for sido in sorted(df_out["region_sido"].dropna().unique()):
            if not sido:
                continue
            sheet_name = str(sido)[:31]
            df_out[df_out["region_sido"] == sido].to_excel(
                writer, sheet_name=sheet_name, index=False
            )

        # 유형별 시트
        for htype in sorted(df_out["housing_type"].dropna().unique()):
            if not htype:
                continue
            sheet_name = f"유형_{htype}"[:31]
            df_out[df_out["housing_type"] == htype].to_excel(
                writer, sheet_name=sheet_name, index=False
            )

    print(f"Excel 저장: {path} ({len(df_out)}건)")
    return path


def export_csv_by_region(engine, output_dir: str = OUTPUT_DIR):
    """시도별 CSV 파일로 내보내기"""
    os.makedirs(output_dir, exist_ok=True)
    df = load_all(engine)
    if df.empty:
        print("데이터 없음.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    drop_cols = ["id", "raw_data"]
    df_out = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    paths = []
    for sido in sorted(df_out["region_sido"].dropna().unique()):
        if not sido:
            continue
        safe_name = sido.replace("/", "_")
        path = os.path.join(output_dir, f"{safe_name}_{timestamp}.csv")
        df_out[df_out["region_sido"] == sido].to_csv(path, index=False, encoding="utf-8-sig")
        paths.append(path)
        print(f"CSV 저장: {path}")

    all_path = os.path.join(output_dir, f"전국_{timestamp}.csv")
    df_out.to_csv(all_path, index=False, encoding="utf-8-sig")
    print(f"전국 CSV: {all_path}")
    return paths


def export_json(engine, output_dir: str = OUTPUT_DIR):
    """JSON 내보내기"""
    os.makedirs(output_dir, exist_ok=True)
    df = load_all(engine)
    if df.empty:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"분양공고_{timestamp}.json")

    records = df.drop(columns=["id", "raw_data"], errors="ignore").to_dict(orient="records")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, default=str)

    print(f"JSON 저장: {path} ({len(records)}건)")
    return path


def print_summary(engine):
    """수집 현황 요약 출력"""
    df = load_all(engine)
    if df.empty:
        print("수집 데이터 없음.")
        return

    print(f"\n{'='*50}")
    print(f"총 수집 공고: {len(df)}건")
    print(f"\n[출처별]")
    print(df["source"].value_counts().to_string())
    print(f"\n[지역별]")
    print(df["region_sido"].value_counts().to_string())
    print(f"\n[유형별]")
    print(df["housing_type"].value_counts().to_string())
    print(f"{'='*50}\n")
