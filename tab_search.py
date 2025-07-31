# 파일 이름: tab_search.py (전략 적용 후 수정된 버전)

import streamlit as st
import datetime
import os
import pandas as pd
import io
from modules import url_builder, data_fetcher, data_processor

# 기본 검색어 설정
DEFAULT_OR_KEYWORDS = (
    "MRAM, PRAM, RRAM, FeRAM, OxRAM, CBRAM, "
    "\"Resistive Random-Access Memory\", \"Magnetoresistive Random-Access Memory\", "
    "\"Ferroelectric Random-Access Memory\", \"non-volatile memory\", \"nonvolatile memory\", "
    "\"emerging memory\", \"next-generation memory\", \"storage class memory\", "
    "\"novel memory\", \"advanced memory\", memristor, memristive"
)

def initialize_session_state():
    """세션 상태를 초기화하는 함수"""
    if 'search_step' not in st.session_state:
        st.session_state.search_step = "start"

def render(): # ✨ 인자는 받지 않습니다.
    """논문 검색, 수집, 정제 워크플로우를 담당하는 UI와 로직을 렌더링합니다."""

    initialize_session_state()

    # ==============================================================================
    # 1. UI (입력 섹션)
    # ==============================================================================

    if st.session_state.search_step in ["start", "done"]:
        with st.container(border=True):
            st.header("1. 검색 조건 설정")

            # --- 필수 입력: 이메일 주소 (강조된 안내 메시지와 함께) ---
            st.info("ℹ️ **반드시 본인의 이메일 주소를 입력해야 검색 결과를 받을 수 있습니다.** (OpenAlex API 정책)")
            email = st.text_input(
                label="API 사용 이메일 주소 (필수)",
                placeholder="your.email@company.com",
                value="",
                key="api_email_input"
            )

            col1, col2 = st.columns(2)

            with col1:
                or_keywords_input = st.text_area("OR 키워드 (하나라도 포함)", value=DEFAULT_OR_KEYWORDS, height=250, key="or_keywords")
            with col2:
                and_keywords_input = st.text_area("AND 키워드 (모두 포함)", "neuromorphic", height=100, key="and_keywords")

                st.markdown("---")
                st.subheader("2. 검색 기간")
                current_year = datetime.datetime.now().year

                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    start_year = st.number_input("시작 연도", min_value=1980, max_value=current_year + 1, value=2015, key='start_year')
                with sub_col2:
                    end_year = st.number_input("종료 연도", min_value=1980, max_value=current_year + 1, value=current_year, key='end_year')

            if start_year > end_year:
                st.error("오류: 시작 연도는 종료 연도보다 클 수 없습니다.")
                st.stop()

            with st.expander("상세 검색 조건 펼치기"):
                type_options = {
                    '학술 논문 (Article)': 'article', '학회 발표 자료 (Conference Paper)': 'conference',
                    '도서 챕터 (Book Chapter)': 'book-chapter', '리뷰 (Review)': 'review', '학위 논문 (Dissertation)': 'dissertation'
                }
                selected_includes = st.multiselect("포함할 문서 유형", options=list(type_options.keys()), default=['학술 논문 (Article)', '학회 발표 자료 (Conference Paper)'], key="doc_types")

                search_mode_option = st.radio("검색 범위", ('넓게 검색 (포괄적)', '정확하게 검색 (핵심적)'), horizontal=True, key="search_mode")

        # --- 데이터 수집 시작 버튼 ---
        if st.button("논문 데이터 수집 및 정제 시작", type="primary", use_container_width=True):
            if not email or "@" not in email:
                st.error("필수 항목인 이메일 주소를 올바르게 입력해주세요.")
            else:
                st.session_state.search_step = "collecting"
                st.session_state.ui_inputs = {
                    "email": email,
                    "or_keywords_input": or_keywords_input,
                    "and_keywords_input": and_keywords_input,
                    "start_year": start_year,
                    "end_year": end_year,
                    "include_types_values": [type_options[key] for key in selected_includes],
                    "search_mode": 'broad' if '넓게' in search_mode_option else 'precise'
                }
                st.rerun()

    # ==============================================================================
    # 2. 데이터 수집 단계 (백그라운드 로직)
    # ==============================================================================
    if st.session_state.search_step == "collecting":
        with st.spinner("1/2 - URL 생성 및 데이터 수집 중..."):
            inputs = st.session_state.ui_inputs.copy()
            search_mode = inputs.pop('search_mode')
            params = url_builder.prepare_params(**inputs)
            if search_mode == 'broad':
                api_url = url_builder.create_broad_query(**params)
            else:
                api_url = url_builder.create_precise_query(**params)
            st.code(f"API URL: {api_url}", language="text")
            DATA_DIR = "data"
            if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
            output_filepath = os.path.join(DATA_DIR, "collected_data.jsonl")
            data_fetcher.fetch_and_save_incrementally(api_url, output_filepath)
            st.session_state['data_filepath'] = output_filepath
            st.session_state.search_step = "processing"
            st.rerun()

    # ==============================================================================
    # 3. 데이터 정제 단계 (백그라운드 로직)
    # ==============================================================================
    if st.session_state.search_step == "processing":
        filepath = st.session_state['data_filepath']
        with st.spinner(f"2/2 - '{os.path.basename(filepath)}' 파일 정제 및 분석 준비 중..."):
            final_df = data_processor.process_and_refine_data(filepath)

            # ✨✨✨ --- 여기가 유일한 핵심 수정 지점 --- ✨✨✨
            # 1. 상태를 직접 수정하는 대신, main.py에 처리할 '액션'을 등록합니다.
            st.session_state.pending_action = ('SEARCH_ACTION', final_df)

            # 2. 이 탭에서 사용했던 임시 데이터(final_df)는 이제 세션에 저장할 필요가 없습니다.
            #    (주석 처리 또는 삭제)
            # st.session_state['final_df'] = final_df

            # 3. 이 탭의 상태를 '완료'로 변경합니다.
            st.session_state.search_step = "done"

            # 4. main.py가 액션을 처리하도록 즉시 재로딩(rerun)을 요청합니다.
            st.rerun()
            # ✨✨✨ --- 수정 끝 --- ✨✨✨

    # ==============================================================================
    # 4. 최종 결과 표시 및 다운로드/초기화
    # ==============================================================================
    if st.session_state.search_step == "done":
        st.subheader("✅ 수집 및 정제 완료")

        # 이제 데이터는 중앙 저장소인 st.session_state.data 에서 가져옵니다.
        final_df = st.session_state.get('data', pd.DataFrame())

        if not final_df.empty and st.session_state.get('data_type') == 'search':
            st.info(f"총 {len(final_df)}개의 논문 데이터가 처리되었습니다. 현재 '검색 모드'가 활성화 되었습니다.")
            with st.expander("처리된 데이터 미리보기"):
                st.dataframe(final_df)

            @st.cache_data
            def convert_df_to_excel(df):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                return output.getvalue()

            excel_data = convert_df_to_excel(final_df)
            st.download_button(label="📥 정제된 데이터(엑셀) 다운로드", data=excel_data, file_name="refined_paper_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            # 이 경우는 다른 탭에서 파일을 업로드하여 '분석 모드'로 전환된 상태일 수 있습니다.
            st.info("새로운 검색을 시작하려면 아래 버튼을 눌러주세요.")

        if st.button("새 검색 시작하기", type="secondary", use_container_width=True):
            # 이 탭 내부의 상태만 초기화합니다.
            keys_to_delete = ['search_step', 'ui_inputs', 'data_filepath', 'api_email_input', 'or_keywords', 'and_keywords', 'start_year', 'end_year', 'doc_types', 'search_mode']
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]

            # 파일 삭제 로직은 그대로 유지
            filepath = os.path.join("data", "collected_data.jsonl")
            if os.path.exists(filepath):
                os.remove(filepath)

            st.rerun()