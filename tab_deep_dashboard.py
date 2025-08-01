# 파일 이름: tab_deep_dashboard.py (무한 루프 최종 해결)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from wordcloud import WordCloud
import re
import io
import base64

# ==============================================================================
# 데이터 클리닝을 위한 전용 함수
# ==============================================================================
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # (이 함수는 변경 없음)
    missing_values = ['nan', 'None', 'none', 'null', '']
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip()
        df[col].replace(missing_values, np.nan, inplace=True)
    numeric_cols = ['publication_year', 'cited_by_count', 'fwci', 'Citation_Percentile']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# ==============================================================================
# 메인 렌더링 함수
# ==============================================================================
def render(df: pd.DataFrame, data_type: str):
    st.header("🔬 키워드 기반 동향 분석")
    st.info("핵심 기술 키워드의 부상과 쇠퇴, 그리고 이를 주도하는 경쟁 구도를 분석합니다.")
    st.markdown("---")

    # "처리 완료된 파일 ID"를 저장하기 위한 session_state 초기화
    if 'processed_file_id' not in st.session_state:
        st.session_state.processed_file_id = None

    # ==========================================================================
    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 파일 업로더 (최종 수정) ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # ==========================================================================
    st.subheader("📁 파일 직접 업로드 (분석 모드 활성화)")
    uploaded_file = st.file_uploader(
        "분석할 엑셀(xlsx) 또는 CSV 파일을 업로드하세요.",
        type=['xlsx', 'csv']
    )

    # 파일이 업로드되었고, 이전에 처리한 파일이 아닐 경우에만 실행
    if uploaded_file is not None and uploaded_file.file_id != st.session_state.processed_file_id:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                new_df = pd.read_excel(uploaded_file)
            else:
                new_df = pd.read_csv(uploaded_file)

            # 액션 등록
            st.session_state.pending_action = ('UPLOAD_ACTION', new_df)

            # (핵심!) 현재 처리한 파일의 ID를 기록하여 중복 실행 방지
            st.session_state.processed_file_id = uploaded_file.file_id

            # 앱 즉시 재실행
            st.success(f"'{uploaded_file.name}' 파일이 성공적으로 업로드되었습니다. 분석이 시작됩니다...")
            st.rerun()

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
            # 에러 발생 시, ID 기록을 초기화하여 재시도 가능하게 함
            st.session_state.processed_file_id = None

    st.markdown("---")
    # ==========================================================================
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 파일 업로더 수정 끝 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    # ==========================================================================

    if data_type != 'analysis':
        st.info("이 대시보드는 '분석 모드'에서만 활성화됩니다. 위에서 파일을 업로드하거나, '논문 검색' 탭에서 데이터를 검색해주세요.")
        return

    # --- 여기서부터는 이전과 동일한, 완벽하게 작동하는 분석 코드입니다 ---

    df = clean_dataframe(df.copy())
    st.success(f"**총 {len(df):,}건**의 데이터를 기반으로 분석을 시작합니다.")
    st.markdown("---")

    keyword_col = 'Keywords(Scores)'
    if keyword_col not in df.columns:
        st.error(f"'{keyword_col}' 컬럼이 없어 심층 동향 분석을 수행할 수 없습니다.")
        return

    keywords_series = df.dropna(subset=[keyword_col])[keyword_col]
    all_keywords_raw = keywords_series.str.split(';').explode()
    pure_keywords = all_keywords_raw.str.split('(').str[0].str.strip()
    pure_keywords = pure_keywords[pure_keywords[pure_keywords != ''].notna()]

    if pure_keywords.empty:
        st.warning("분석할 유효한 키워드가 없습니다.")
        return

    keyword_counts = pure_keywords.value_counts()

    # (이하 모든 분석 및 시각화 코드는 이전과 동일합니다)
    st.subheader("1. 글로벌 핵심 키워드 분석")
    st.markdown("##### **1-1. 전체 키워드 빈도**")
    col1, col2 = st.columns([1, 1], vertical_alignment="center")

    with col1:
        top_20_keywords = keyword_counts.nlargest(20)
        fig_bar = px.bar(top_20_keywords, x=top_20_keywords.values, y=top_20_keywords.index, orientation='h', labels={'x': '빈도수', 'y': '키워드'}, height=500)
        fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
        fig_bar.update_traces(marker_color='#418cdc' )
        st.plotly_chart(fig_bar, use_container_width=True)
        with st.expander("데이터 테이블 보기"):
            st.dataframe(top_20_keywords.reset_index(name='빈도수').rename(columns={'index': '키워드'}), use_container_width=True)

    with col2:
        wordcloud_data = keyword_counts.to_dict()
        wc = WordCloud(
            width=800, height=500, background_color='white',
            colormap='viridis', max_words=150, relative_scaling=0.3, font_path='fonts/Lato-Black.ttf'
        ).generate_from_frequencies(wordcloud_data)

        img_buffer = io.BytesIO()
        wc.to_image().save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()

        st.markdown(
            f'<div style="text-align: center">'
            f'  <img src="data:image/png;base64,{img_base64}" style="width: 450px; max-width: 100%;">'
            f'</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("##### **1-2. 전체 키워드 연도별 트렌드**")
    df_trend_global = df.dropna(subset=[keyword_col, 'publication_year']).copy()
    df_trend_global['publication_year'] = pd.to_numeric(df_trend_global['publication_year'], errors='coerce').dropna().astype(int)
    df_trend_global['keywords'] = df_trend_global[keyword_col].str.split(';').apply(lambda x: [kw.split('(')[0].strip() for kw in x if kw.strip()])
    df_trend_global = df_trend_global.explode('keywords')
    df_trend_global = df_trend_global[df_trend_global['keywords'] != '']
    top_10_global_keywords = keyword_counts.nlargest(10).index.tolist()
    trend_data_global = df_trend_global[df_trend_global['keywords'].isin(top_10_global_keywords)]
    trend_counts_global = trend_data_global.groupby(['publication_year', 'keywords']).size().unstack(fill_value=0)
    for kw in top_10_global_keywords:
        if kw not in trend_counts_global.columns:
            trend_counts_global[kw] = 0
    trend_counts_global = trend_counts_global[top_10_global_keywords]

    fig_stream_global = px.bar(trend_counts_global, x=trend_counts_global.index, y=trend_counts_global.columns, title="<b>전체 데이터의 연도별 핵심 키워드 빈도수 변화</b>", labels={'publication_year': '발행연도', 'value': '키워드 빈도수', 'variable': '키워드'}, category_orders={"variable": top_10_global_keywords})
    fig_stream_global.update_layout(barmode='stack', legend_title_text='Top 10 키워드')
    st.plotly_chart(fig_stream_global, use_container_width=True)
    with st.expander("연도별 빈도수 데이터 보기"):
        st.dataframe(trend_counts_global.sort_index(ascending=False), use_container_width=True)

    st.markdown("---")
    st.subheader("2. 주요 국가별 키워드 분석")
    country_col = 'First_Author_Country'
    if country_col not in df.columns:
        st.warning(f"'{country_col}' 컬럼이 없어 국가별 분석을 할 수 없습니다.")
    else:
        country_series = df.dropna(subset=[country_col])[country_col].str.split(';').explode().str.strip()
        top_countries = country_series[country_series != ''].value_counts().nlargest(20).index.tolist()
        selected_country = st.selectbox("분석할 국가를 선택하세요:", options=top_countries, key='deepdive_country_selector')

        if selected_country:
            country_df = df[df[country_col].str.contains(re.escape(selected_country), na=False)].copy()
            st.markdown(f"##### **2-1. {selected_country}의 핵심 키워드 빈도**")
            country_keywords_series = country_df.dropna(subset=[keyword_col])[keyword_col]
            country_all_keywords_raw = country_keywords_series.str.split(';').explode()
            country_pure_keywords = country_all_keywords_raw.str.split('(').str[0].str.strip()
            country_pure_keywords = country_pure_keywords[country_pure_keywords[country_pure_keywords != ''].notna()]

            if not country_pure_keywords.empty:
                country_keyword_counts = country_pure_keywords.value_counts()
                c_col1, c_col2 = st.columns([1, 1], vertical_alignment="center")
                with c_col1:
                    c_top_20 = country_keyword_counts.nlargest(20)
                    c_fig_bar = px.bar(c_top_20, x=c_top_20.values, y=c_top_20.index, orientation='h', labels={'x': '빈도수', 'y': '키워드'}, height=500)
                    c_fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
                    c_fig_bar.update_traces(marker_color='#418cdc' )
                    st.plotly_chart(c_fig_bar, use_container_width=True)
                    with st.expander(f"{selected_country} 키워드 데이터 보기"):
                        st.dataframe(c_top_20.reset_index(name='빈도수').rename(columns={'index': '키워드'}), use_container_width=True)

                with c_col2:
                    c_wc_data = country_keyword_counts.to_dict()
                    c_wc = WordCloud(
                        width=800, height=500, background_color='white',
                        colormap='cividis', max_words=150, relative_scaling=0.3, font_path='fonts/Lato-Black.ttf'
                    ).generate_from_frequencies(c_wc_data)

                    c_img_buffer = io.BytesIO()
                    c_wc.to_image().save(c_img_buffer, format='PNG')
                    c_img_base64 = base64.b64encode(c_img_buffer.getvalue()).decode()

                    st.markdown(
                        f'<div style="text-align: center">'
                        f'  <img src="data:image/png;base64,{c_img_base64}" style="width: 450px; max-width: 100%;">'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.warning(f"'{selected_country}'에 대한 키워드 데이터가 없습니다.")

            st.markdown(f"##### **2-2. {selected_country}의 연도별 키워드 트렌드**")
            country_df_trend = country_df.dropna(subset=[keyword_col, 'publication_year']).copy()
            country_df_trend['publication_year'] = pd.to_numeric(country_df_trend['publication_year'], errors='coerce').dropna().astype(int)
            country_df_trend['keywords'] = country_df_trend[keyword_col].str.split(';').apply(lambda x: [kw.split('(')[0].strip() for kw in x if kw.strip()])
            country_df_trend = country_df_trend.explode('keywords')
            country_df_trend = country_df_trend[country_df_trend['keywords'] != '']
            country_trend_data = country_df_trend[country_df_trend['keywords'].isin(top_10_global_keywords)]
            country_trend_counts = country_trend_data.groupby(['publication_year', 'keywords']).size().unstack(fill_value=0)
            for kw in top_10_global_keywords:
                if kw not in country_trend_counts.columns:
                    country_trend_counts[kw] = 0
            country_trend_counts = country_trend_counts[top_10_global_keywords]

            if not country_trend_counts.empty:
                country_fig_stream = px.bar(country_trend_counts, x=country_trend_counts.index, y=country_trend_counts.columns, title=f"<b>{selected_country}의 연도별 핵심 키워드 빈도수 변화 (Global Top 10 기준)</b>", labels={'publication_year': '발행연도', 'value': '키워드 빈도수', 'variable': '키워드'}, category_orders={"variable": top_10_global_keywords})
                country_fig_stream.update_layout(barmode='stack', legend_title_text='Top 10 키워드')
                st.plotly_chart(country_fig_stream, use_container_width=True)
                with st.expander("연도별 빈도수 데이터 보기"):
                    st.dataframe(country_trend_counts.sort_index(ascending=False), use_container_width=True)
            else:
                st.warning(f"{selected_country}에서 글로벌 Top 10 키워드에 대한 데이터가 부족하여 트렌드를 표시할 수 없습니다.")

    st.markdown("---")
    st.subheader("3. 특정 기술의 글로벌 리더 추적")
    institution_col = 'All_Institutions'
    if institution_col not in df.columns:
        st.warning(f"'{institution_col}' 컬럼이 없어 기관 분석을 할 수 없습니다.")
    else:
        selected_keyword_for_inst = st.selectbox("분석할 핵심 기술(키워드)을 선택하세요:", options=keyword_counts.nlargest(50).index, key="inst_keyword_select")
        if selected_keyword_for_inst:
            keyword_df = df[df[keyword_col].str.contains(re.escape(selected_keyword_for_inst), na=False)].copy()
            inst_series = keyword_df.dropna(subset=[institution_col])[institution_col].str.split(';').explode().str.strip()
            non_blank_inst = inst_series[inst_series != '']
            if not non_blank_inst.empty:
                inst_counts = non_blank_inst.value_counts().nlargest(15)
                fig_inst = px.bar(inst_counts, x=inst_counts.values, y=inst_counts.index, orientation='h', title=f"<b>'{selected_keyword_for_inst}' 기술 선도 연구기관 Top 15</b>", labels={'x': '논문 수', 'y': '연구 기관'})
                fig_inst.update_layout(yaxis={'categoryorder': 'total ascending'})
                fig_inst.update_traces(marker_color='#418cdc' )
                st.plotly_chart(fig_inst, use_container_width=True)
                with st.expander("데이터 테이블 보기"):
                    st.dataframe(inst_counts.reset_index(name='논문 수').rename(columns={'index': '연구 기관'}), use_container_width=True)
            else:
                st.warning(f"'{selected_keyword_for_inst}' 키워드를 포함한 논문의 기관 정보가 없습니다.")