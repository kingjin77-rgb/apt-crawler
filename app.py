"""
아파트 공고 수집기 — Streamlit Web UI
청약홈 · LH · SH 분양공고 자동수집
"""
import streamlit as st
import subprocess
import sys
import os
import json
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(
    page_title="아파트 공고 수집기",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏢 아파트 분양공고 자동 수집기")
st.caption("청약홈 · LH · SH 공고 자동수집 | Excel·CSV 다운로드")

# ── 사이드바 설정 ──
st.sidebar.header("⚙️ 수집 설정")

sources = st.sidebar.multiselect(
    "수집 출처",
    ["applyhome (청약홈)", "lh (LH공사)", "sh (SH공사)", "public (공공데이터)", "officetel (오피스텔·도시형)", "building (건축물대장)"],
    default=["applyhome (청약홈)", "lh (LH공사)", "officetel (오피스텔·도시형)"]
)

regions = st.sidebar.text_input(
    "지역 필터 (쉼표 구분, 비워두면 전국)",
    placeholder="서울, 경기, 부산"
)

export_format = st.sidebar.selectbox(
    "내보내기 형식",
    ["excel", "csv", "json"]
)

no_detail = st.sidebar.checkbox("빠른 목록만 (상세 수집 생략)", value=False)

st.sidebar.info(
    "⚠️ 처음 실행 시 웹드라이버 설치로 시간이 걸릴 수 있습니다."
)

# ── 직접 크롤러 연동 (subprocess 방식) ──
def run_crawler(source_codes, region_list, no_detail_flag):
    """main.py를 subprocess로 실행하고 결과 파일 반환"""
    cmd = [sys.executable, "main.py"]

    if source_codes:
        cmd += ["--sources"] + source_codes
    if region_list:
        cmd += ["--regions"] + region_list
    if no_detail_flag:
        cmd.append("--no-detail")
    cmd += ["--export", "excel", "csv"]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.stdout, result.stderr

# ── API 기반 직접 조회 (청약홈 공공API) ──
import requests

def fetch_applyhome_api(region_nm=""):
    """청약홈 공공 API 직접 호출 (API 키 불필요 오픈 데이터)"""
    url = "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListAjax.do"
    payload = {
        "orderBy": "RCRIT_PBLANC_DE",
        "page": 1,
        "perPage": 50,
        "houseSecd": "01",  # 아파트
        "sido": region_nm,
        "gugun": "",
        "houseName": "",
    }
    try:
        res = requests.post(url, data=payload, timeout=15)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def fetch_lh_api():
    """LH 청약센터 공고 API"""
    url = "https://api.lh.or.kr/lhLeaseNoticeInfo/getLeaseNoticeInfoList"
    params = {
        "serviceKey": "DEMO",  # 공공API 키 (data.go.kr에서 발급)
        "numOfRows": 30,
        "pageNo": 1,
        "type": "json"
    }
    try:
        res = requests.get(url, params=params, timeout=15)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

# ── 메인 UI ──
tab1, tab2, tab3 = st.tabs(["🔍 공고 검색", "📊 수집 결과", "⚙️ 직접 실행"])

with tab1:
    st.subheader("🏠 청약홈 공고 실시간 조회")

    col1, col2 = st.columns([3, 1])
    with col1:
        region_input = st.selectbox(
            "시도 선택",
            ["", "서울특별시", "경기도", "인천광역시", "부산광역시",
             "대구광역시", "광주광역시", "대전광역시", "울산광역시",
             "세종특별자치시", "강원도", "충청북도", "충청남도",
             "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도"]
        )
    with col2:
        if st.button("🔍 검색", use_container_width=True, type="primary"):
            with st.spinner("청약홈 공고 조회 중..."):
                data = fetch_applyhome_api(region_input)
                st.session_state["search_result"] = data

    if "search_result" in st.session_state:
        data = st.session_state["search_result"]
        if "error" in data:
            st.error(f"조회 실패: {data['error']}")
            st.info("청약홈 API는 사이트 정책에 따라 접근이 제한될 수 있습니다. '직접 실행' 탭을 이용하세요.")
        else:
            try:
                items = data.get("data", data.get("list", []))
                if items:
                    df = pd.DataFrame(items)
                    st.success(f"✅ {len(df)}건 조회됨")
                    st.dataframe(df, use_container_width=True)

                    buf = BytesIO()
                    df.to_excel(buf, index=False)
                    st.download_button("📥 Excel 다운로드", buf.getvalue(), "공고목록.xlsx", use_container_width=True)
                else:
                    st.warning("조회된 공고가 없습니다.")
                    st.json(data)
            except Exception as e:
                st.error(f"데이터 파싱 오류: {e}")
                st.json(data)

with tab2:
    st.subheader("📂 저장된 수집 결과")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    if os.path.exists(output_dir):
        files = [f for f in os.listdir(output_dir) if f.endswith(('.xlsx', '.csv', '.json'))]
        if files:
            selected = st.selectbox("파일 선택", sorted(files, reverse=True))
            fpath = os.path.join(output_dir, selected)

            if selected.endswith('.xlsx'):
                df = pd.read_excel(fpath)
                st.dataframe(df, use_container_width=True)
                with open(fpath, 'rb') as f:
                    st.download_button("📥 다운로드", f.read(), selected, use_container_width=True)
            elif selected.endswith('.csv'):
                df = pd.read_csv(fpath, encoding='utf-8-sig')
                st.dataframe(df, use_container_width=True)
                with open(fpath, 'r', encoding='utf-8-sig') as f:
                    st.download_button("📥 다운로드", f.read(), selected, use_container_width=True)
        else:
            st.info("저장된 파일 없음. '직접 실행' 탭에서 수집 후 확인하세요.")
    else:
        st.info("output 폴더 없음. 수집 후 자동 생성됩니다.")

with tab3:
    st.subheader("⚙️ 크롤러 직접 실행")
    st.warning("Selenium 기반 크롤러 실행 — 처음 실행 시 Chrome 드라이버 자동 설치 (수분 소요)")

    src_map = {
        "applyhome (청약홈)": "applyhome",
        "lh (LH공사)": "lh",
        "sh (SH공사)": "sh",
        "public (공공데이터)": "public",
        "officetel (오피스텔·도시형)": "officetel",
        "building (건축물대장)": "building"
    }
    sel_sources = [src_map[s] for s in sources if s in src_map]
    sel_regions = [r.strip() for r in regions.split(",") if r.strip()] if regions else []

    st.info(f"**설정:** 출처={sel_sources or '전체'} · 지역={sel_regions or '전국'} · 상세수집={'생략' if no_detail else '포함'}")

    if st.button("🚀 크롤러 실행", type="primary", use_container_width=True):
        with st.spinner("수집 중... (최대 5분 소요)"):
            try:
                stdout, stderr = run_crawler(sel_sources, sel_regions, no_detail)
                if stdout:
                    st.success("✅ 수집 완료")
                    st.text(stdout)
                if stderr:
                    st.warning("경고/오류:")
                    st.text(stderr[:2000])
                st.info("'수집 결과' 탭에서 파일 다운로드 가능합니다.")
            except subprocess.TimeoutExpired:
                st.error("시간 초과 (5분). 지역을 좁히거나 빠른 목록 옵션을 사용하세요.")
            except Exception as e:
                st.error(f"실행 오류: {e}")
