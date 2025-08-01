# 파일 이름: tab_basic_dashboard.py (expander 추가 완료된 전체 코드)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

def render(df: pd.DataFrame, data_type: str):
    st.header("📊 데이터 기본 동향")

    # 1. 현재 모드가 '분석 모드'일 때만 대시보드를 보여줍니다.
    if data_type == 'analysis':
        st.info("현재 업로드된 데이터의 전체적인 통계와 분포를 요약하여 보여줍니다.")
        st.markdown("---")

        # --- 1. 한눈에 보는 핵심 요약 ---
        st.subheader("🔢 한눈에 보는 핵심 요약")

        # 각 컬럼의 존재 여부를 확인하며 안전하게 계산
        total_papers = len(df)
        avg_citations = df.get('cited_by_count', pd.Series(dtype='float')).mean()

        if 'All_Authors' in df.columns:
            total_authors = df['All_Authors'].dropna().str.split(';').explode().str.strip().nunique()
        else: total_authors = "N/A"

        unique_first_authors = df.get('First_Author_Name', pd.Series(dtype='str')).nunique()

        if 'Corresponding_Author_Names' in df.columns:
            unique_corr_authors = df['Corresponding_Author_Names'].dropna().str.split(';').explode().str.strip().nunique()
        else: unique_corr_authors = "N/A"

        if 'All_Institutions' in df.columns:
            total_institutions = df['All_Institutions'].dropna().str.split(';').explode().str.strip().nunique()
        else: total_institutions = "N/A"

        unique_first_inst = df.get('First_Author_Institution', pd.Series(dtype='str')).nunique()

        if 'Corresponding_Institution_Names' in df.columns:
            unique_corr_inst = df['Corresponding_Institution_Names'].dropna().str.split(';').explode().str.strip().nunique()
        else: unique_corr_inst = "N/A"

        # 요약 정보 탭으로 표시
        tab1, tab2, tab3 = st.tabs(["종합 현황", "👤 연구자 현황", "🏢 연구기관 현황"])
        with tab1:
            col1, col2 = st.columns(2)
            col1.metric("총 논문 수", f"{total_papers:,}")
            col2.metric("평균 피인용 수", f"{avg_citations:.1f}" if pd.notna(avg_citations) else "N/A")
        with tab2:
            col1, col2, col3 = st.columns(3)
            col1.metric("총 저자 수(전체)", f"{total_authors:,}" if isinstance(total_authors, int) else total_authors)
            col2.metric("주저자 수(고유)", f"{unique_first_authors:,}")
            col3.metric("교신저자 수(고유)", f"{unique_corr_authors:,}" if isinstance(unique_corr_authors, int) else unique_corr_authors)
        with tab3:
            col1, col2, col3 = st.columns(3)
            col1.metric("총 기관 수(전체)", f"{total_institutions:,}" if isinstance(total_institutions, int) else total_institutions)
            col2.metric("주저자 소속기관 수", f"{unique_first_inst:,}")
            col3.metric("교신저자 소속기관 수", f"{unique_corr_inst:,}" if isinstance(unique_corr_inst, int) else unique_corr_inst)
        st.markdown("---")

        # --- 2. 결측치 현황 ---
        with st.expander("분석 데이터 상세 정보 보기 (결측치 현황)"):
            total_rows = len(df)
            key_fields = {
                'Corresponding_Author_Names': '교신저자', 'First_Author_Country': '주저자 국가', 'fwci': 'FWCI 지수'
            }
            summary_data = []
            for field, name in key_fields.items():
                if field in df.columns:
                    valid_count = df[field].notna().sum()
                    missing_rate = (1 - valid_count / total_rows) * 100 if total_rows > 0 else 0
                    summary_data.append({"항목": name, "데이터 보유율": f"{100-missing_rate:.1f}%", "결측률": f"{missing_rate:.1f}%"})

            if summary_data:
                st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)
            st.info("**FWCI (Field-Weighted Citation Impact):** 주제 분야, 발행 연도, 문서 유형이 비슷한 다른 논문들과 비교하여, 해당 논문이 받은 인용 수를 정규화한 '질적 영향력' 지표입니다. (FWCI > 1 이면 세계 평균 이상)")
        st.markdown("---")

        # --- 3. 기본 동향 시각화 ---
        st.subheader("📈 주요 항목별 분포")
        col_graph1, col_graph2 = st.columns(2)

        with col_graph1:
            st.markdown("###### 연도별 논문 발행 동향")
            if 'publication_year' in df.columns and df['publication_year'].notna().any():
                yearly_counts = df['publication_year'].dropna().astype(int).value_counts().sort_index()
                fig_yearly = px.bar(yearly_counts, x=yearly_counts.index, y=yearly_counts.values, labels={'x': '발행 연도', 'y': '논문 수'})
                fig_yearly.update_traces(marker_color='#418cdc' )
                st.plotly_chart(fig_yearly, use_container_width=True)

                with st.expander("데이터 보기"):
                    st.dataframe(yearly_counts)
            else:
                st.warning("발행 연도 데이터가 없어 분석할 수 없습니다.")

            st.markdown("###### 국가별 연구 동향 (주저자 국가 기준 Top 15)")
            if 'First_Author_Country' in df.columns and df['First_Author_Country'].notna().any():
                country_series = df['First_Author_Country'].dropna().str.split(';').explode().str.strip()
                country_counts = country_series.value_counts().nlargest(15)
                fig_country = px.bar(country_counts, y=country_counts.index, x=country_counts.values, orientation='h', labels={'y': '국가', 'x': '논문 수'})
                fig_country.update_traces(marker_color='#418cdc')
                fig_country.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_country, use_container_width=True)

                with st.expander("데이터 보기"):
                    st.dataframe(country_counts)
            else:
                st.warning("주저자 국가 데이터가 없어 분석할 수 없습니다.")

        with col_graph2:
            st.markdown("###### 핵심 연구 기관 (논문 수 기준 Top 15)")
            if 'All_Institutions' in df.columns and df['All_Institutions'].notna().any():
                institution_series = df['All_Institutions'].dropna().str.split(';').explode().str.strip()
                non_blank_institutions = institution_series[institution_series != '']
                institution_counts = non_blank_institutions.value_counts().nlargest(15)
                fig_inst = px.bar(institution_counts, y=institution_counts.index, x=institution_counts.values, orientation='h', labels={'y': '연구 기관', 'x': '논문 수'})
                fig_inst.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_inst.update_traces(marker_color='#418cdc')

                st.plotly_chart(fig_inst, use_container_width=True)

                with st.expander("데이터 보기"):
                    st.dataframe(institution_counts)
            else:
                st.warning("연구 기관 데이터가 없어 분석할 수 없습니다.")

            st.markdown("###### 주요 연구 토픽 (Primary Topic 기준 Top 15)")
            if 'Primary_Topic(Score)' in df.columns and df['Primary_Topic(Score)'].notna().any():
                df['Primary_Topic_Clean'] = df['Primary_Topic(Score)'].str.split('(').str[0].str.strip()
                topic_counts = df['Primary_Topic_Clean'].value_counts().nlargest(15)
                fig_topic = px.bar(topic_counts, y=topic_counts.index, x=topic_counts.values, orientation='h', labels={'y': '주요 토픽', 'x': '빈도 수'})
                fig_topic.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_topic.update_traces(marker_color='#418cdc')
                st.plotly_chart(fig_topic, use_container_width=True)

                with st.expander("데이터 보기"):
                    st.dataframe(topic_counts)
            else:
                st.warning("연구 토픽 데이터가 없어 분석할 수 없습니다.")

    # 2. 현재 모드가 '분석 모드'가 아닐 경우 파일 업로더를 표시
    else:
        st.info("새로운 데이터를 분석하려면 아래에서 파일을 업로드해주세요.")

        uploaded_file = st.file_uploader(
            "분석할 엑셀(csv) 파일을 업로드하세요.",
            type=['csv', 'xlsx'],
            key="dashboard_uploader"
        )

        if uploaded_file is not None:
            # 파일이 업로드되면, main.py에 처리할 '액션'을 등록합니다.
            try:
                uploaded_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                # '작업 지시서' 등록
                st.session_state.pending_action = ('UPLOAD_ACTION', uploaded_df)
                # main.py가 액션을 처리하도록 즉시 재로딩 요청
                st.rerun()
            except Exception as e:
                st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")