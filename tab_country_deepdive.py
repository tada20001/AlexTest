# 파일 이름: tab_country_deepdive.py (파일 업로더 추가 및 무한 루프 해결)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from itertools import combinations

try:
    import pycountry_convert as pc
    PYCOUNTRY_AVAILABLE = True
except ImportError:
    PYCOUNTRY_AVAILABLE = False

# ==============================================================================
# 데이터 클리닝 및 전처리 함수
# ==============================================================================
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # (이 함수는 변경 없음)
    missing_values = ['nan', 'None', 'none', 'null', '']
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip(); df[col].replace(missing_values, np.nan, inplace=True)
    numeric_cols = ['publication_year', 'cited_by_count', 'fwci', 'Citation_Percentile', 'Is_Top_10_Percent']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    if 'All_Countries' in df.columns:
        df['All_Countries'] = df['All_Countries'].fillna('')
        df['country_list'] = df['All_Countries'].str.split(';').apply(
            lambda lst: sorted([country.strip() for country in lst if country.strip()])
        )
    else: df['country_list'] = [[] for _ in range(len(df))]
    return df

# ==============================================================================
# 캐시 함수들은 변경 없음
# ==============================================================================
@st.cache_data
def get_target_country_data(_df, country_code):
    if 'country_list' not in _df.columns: return pd.DataFrame()
    return _df[_df['country_list'].apply(lambda x: country_code in x)].copy()

@st.cache_data
def calculate_country_kpis(_target_country_df, _all_df, country_code):
    if _target_country_df.empty: return {}
    exploded_country_df = _all_df.explode('country_list')
    paper_counts = exploded_country_df['country_list'].value_counts()
    citation_counts = exploded_country_df.groupby('country_list')['cited_by_count'].sum().sort_values(ascending=False)
    global_collab_rate = _all_df['country_list'].apply(lambda x: len(x) > 1).mean() * 100

    kpis = {'total_papers': len(_target_country_df),
            'world_rank_papers': paper_counts.index.get_loc(country_code) + 1 if country_code in paper_counts.index else 'N/A',
            'total_citations': _target_country_df['cited_by_count'].sum(),
            'world_rank_citations': citation_counts.index.get_loc(country_code) + 1 if country_code in citation_counts.index else 'N/A',
            'avg_fwci': _target_country_df['fwci'].mean(),
            'top_10_percent_rate': _target_country_df['Is_Top_10_Percent'].dropna().mean() * 100 if 'Is_Top_10_Percent' in _target_country_df.columns else 0,
            'international_collab_rate': _target_country_df['country_list'].apply(lambda x: len(x) > 1).mean() * 100,
            'global_collab_rate': global_collab_rate}
    return kpis

@st.cache_data
def get_trend_data(_df, country_code):
    country_df = get_target_country_data(_df, country_code)
    if country_df.empty: return pd.DataFrame()
    trend = country_df.groupby('publication_year').agg(논문_수=('doi', 'count'), 평균_FWCI=('fwci', 'mean')).reset_index()
    trend['country'] = country_code
    return trend

@st.cache_data
def get_collaboration_data(_target_country_df, country_code):
    if _target_country_df.empty: return pd.DataFrame()
    exploded_df = _target_country_df.explode('country_list')
    partners_df = exploded_df[(exploded_df['country_list'] != country_code) & (exploded_df['country_list'] != '')].copy()
    collaboration_stats = partners_df.groupby('country_list').agg(Collaboration_Count=('doi', 'count'), Avg_FWCI=('fwci', 'mean')).reset_index()
    collaboration_stats.rename(columns={'country_list': 'Partner_Country'}, inplace=True)
    return collaboration_stats

def get_country_name(code):
    if PYCOUNTRY_AVAILABLE:
        try: return pc.country_alpha2_to_country_name(code)
        except (KeyError, TypeError): return code
    return code

# ==============================================================================
# 메인 렌더링 함수
# ==============================================================================
def render(df: pd.DataFrame, data_type: str):
    st.header("🌐 국가별 연구 경쟁력 동향 대시보드")
    st.info("국가를 선택하여 해당 국가의 연구 생산성, 영향력, 협력 동향을 글로벌 관점에서 분석합니다.")
    st.markdown("---")

    # ==========================================================================
    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 파일 업로더 추가 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    # ==========================================================================
    # "처리 완료된 파일 ID"를 저장하기 위한 session_state 초기화
    if 'country_processed_file_id' not in st.session_state:
        st.session_state.country_processed_file_id = None

    st.subheader("📁 파일 직접 업로드")
    uploaded_file = st.file_uploader(
        "분석할 엑셀(xlsx) 또는 CSV 파일을 업로드하세요.",
        type=['xlsx', 'csv'],
        key="country_deepdive_file_uploader" # 다른 탭과 겹치지 않는 고유한 key 사용
    )

    # 파일이 업로드되었고, 이전에 처리한 파일이 아닐 경우에만 실행
    if uploaded_file is not None and uploaded_file.file_id != st.session_state.country_processed_file_id:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                new_df = pd.read_excel(uploaded_file)
            else:
                new_df = pd.read_csv(uploaded_file)

            st.session_state.pending_action = ('UPLOAD_ACTION', new_df)
            st.session_state.country_processed_file_id = uploaded_file.file_id

            st.success(f"'{uploaded_file.name}' 파일이 성공적으로 업로드되었습니다. 분석이 시작됩니다...")
            st.rerun()

        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
            st.session_state.country_processed_file_id = None

    st.markdown("---")
    # ==========================================================================
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ 파일 업로더 수정 끝 ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
    # ==========================================================================


    if data_type != 'analysis':
        st.info("위에서 파일을 업로드하거나, '논문 검색' 탭에서 데이터를 검색해주세요.")
        return

    # --- 여기서부터는 'analysis' 모드일 때만 실행 (기존 코드와 동일) ---

    df = clean_dataframe(df.copy())

    st.success(f"**총 {len(df):,}건**의 데이터를 기반으로 분석을 시작합니다.")
    st.markdown("---")

    all_countries_list = sorted(list(df.explode('country_list')['country_list'].str.strip().replace('', np.nan).dropna().unique()))
    if not all_countries_list:
        st.warning("데이터에서 유효한 국가 코드를 찾을 수 없습니다.")
        return

    default_ix = all_countries_list.index('KR') if 'KR' in all_countries_list else 0
    target_country_code = st.selectbox('분석할 국가를 선택하세요.', options=all_countries_list, index=default_ix, format_func=get_country_name, key='country_deepdive_selector')
    target_country_name = get_country_name(target_country_code)
    st.markdown("---")

    target_country_df = get_target_country_data(df, target_country_code)
    if target_country_df.empty:
        st.error(f"데이터에서 '{target_country_name}' 관련 논문을 찾을 수 없습니다.")
        return

    st.subheader(f"📊 {target_country_name} R&D 핵심 지표 (vs Global)")
    kpis = calculate_country_kpis(target_country_df, df, target_country_code)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("논문 수", f"{kpis.get('total_papers', 0):,}", f"세계 {kpis.get('world_rank_papers', 'N/A')}위")
    c2.metric("피인용 수", f"{kpis.get('total_citations', 0):,}", f"세계 {kpis.get('world_rank_citations', 'N/A')}위")
    c3.metric("FWCI", f"{kpis.get('avg_fwci', 0):.2f}", f"{kpis.get('avg_fwci', 1.0) - 1.0:.2f} vs 세계 평균(1.0)")
    c4.metric("Top 10% 논문", f"{kpis.get('top_10_percent_rate', 0):.1f}%", f"{kpis.get('top_10_percent_rate', 10.0) - 10.0:+.1f}%p")
    c5.metric("국제 협력", f"{kpis.get('international_collab_rate', 0):.1f}%", f"{kpis.get('international_collab_rate', 0) - kpis.get('global_collab_rate', 0):+.1f}%p")
    st.markdown("---")

    st.subheader(f"📈 {target_country_name}의 글로벌 경쟁력 비교 및 트렌드")
    competitor_list = [c for c in all_countries_list if c != target_country_code]
    default_competitors = ['US', 'CN', 'JP', 'DE', 'GB', 'IN']
    default_selection = [c for c in default_competitors if c in competitor_list]
    selected_countries = st.multiselect('비교할 경쟁 국가를 선택하세요', options=competitor_list, default=default_selection)

    countries_to_analyze = [target_country_code] + selected_countries
    trend_data_list = [get_trend_data(df, country) for country in countries_to_analyze]

    if trend_data_list:
        combined_trend = pd.concat(trend_data_list)
        if not combined_trend.empty:
            pivot_df = combined_trend.pivot(index='publication_year', columns='country', values='논문_수').sort_index().fillna(0)

            tab_growth, tab_share_area, tab_share_heat = st.tabs(["① 연구 성장률", "② 논문 점유율 (추세)", "③ 논문 점유율 (수치)"])

            with tab_growth:
                st.info("선택한 기간 동안의 연평균 성장률(CAGR)을 비교합니다. 이는 기간 동안의 평균적인 연간 성장세를 나타냅니다.")

                min_year = int(pivot_df.index.min())
                max_year = int(pivot_df.index.max())

                col1, col2 = st.columns(2)
                with col1:
                    start_year = st.number_input("분석 시작 연도", min_value=min_year, max_value=max_year, value=min_year)
                with col2:
                    end_year = st.number_input("분석 종료 연도", min_value=min_year, max_value=max_year, value=max_year)

                if start_year >= end_year:
                    st.error("오류: 시작 연도는 종료 연도보다 작아야 합니다.")
                else:
                    filtered_df = pivot_df.loc[start_year:end_year]
                    cagr_results = {}
                    num_years = end_year - start_year

                    for country in filtered_df.columns:
                        start_value = filtered_df[country].loc[start_year]
                        end_value = filtered_df[country].loc[end_year]

                        if start_value > 0 and num_years > 0:
                            cagr = ((end_value / start_value) ** (1 / num_years) - 1) * 100
                            cagr_results[country] = cagr
                        else:
                            cagr_results[country] = np.nan

                    cagr_series = pd.Series(cagr_results).dropna().sort_values()

                    if cagr_series.empty:
                        st.warning("선택된 기간의 데이터로 성장률을 계산할 수 없습니다.")
                    else:
                        fig = px.bar(x=cagr_series.values, y=cagr_series.index, orientation='h',
                                     title=f"주요국 연평균 성장률(CAGR) 비교 ({start_year}–{end_year})",
                                     labels={'x': '연평균 성장률 (%)', 'y': '국가'}, text_auto='.2f')
                        fig.update_traces(marker_color='#418cdc', texttemplate='%{x:.2f}%', textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)

            with tab_share_area:
                st.info("선택된 국가 그룹 내에서 각국의 논문 점유율(%) 추세를 보여줍니다.")
                fig = px.area(pivot_df, title='주요국 논문 점유율 변화', groupnorm='percent',
                              labels={'publication_year': '발행 연도', 'value': '점유율 (%)', 'country': '국가'})
                st.plotly_chart(fig, use_container_width=True)

            with tab_share_heat:
                st.info("각 연도/국가의 논문 점유율(%) 수치를 히트맵으로 비교합니다.")
                share_df = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
                fig = px.imshow(share_df.T, text_auto='.1f', aspect="auto",
                                labels=dict(x="발행 연도", y="국가", color="점유율 (%)"), title="주요국 논문 점유율")
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader(f"🤝 {target_country_name}의 글로벌 협력 동향 분석")
    collab_df = get_collaboration_data(target_country_df, target_country_code)

    if collab_df.empty:
        st.info(f"{target_country_name}의 국제 협력 연구 데이터가 없습니다.")
    else:
        tab_main_partner, tab_trend, tab_matrix = st.tabs(["① 주요 협력국 현황", "② 협력 트렌드 분석", "③ 협력 네트워크 매트릭스"])
        top_n = st.slider("분석할 상위 협력 국가 수:", min_value=5, max_value=len(collab_df), value=min(10, len(collab_df)), key="collab_slider")
        top_partners_df = collab_df.sort_values(by="Collaboration_Count", ascending=False).head(top_n)
        top_partner_countries = top_partners_df['Partner_Country'].tolist()

        with tab_main_partner:
            st.info(f"**{target_country_name}**와(과) 가장 많이 협력하는 국가들을 보여줍니다.")
            fig_bar = px.bar(top_partners_df, x='Collaboration_Count', y='Partner_Country', orientation='h', title=f'상위 {top_n}개 협력 국가별 논문 수',
                             labels={'Collaboration_Count': '협력 논문 수', 'Partner_Country': '협력 국가'}, text='Collaboration_Count')
            fig_bar.update_traces(textangle=0, textposition='inside', insidetextanchor='middle', marker_color='#418cdc')
            fig_bar.update_layout(xaxis_title="협력 논문 수", yaxis_title="협력 국가", xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray'),
                                  yaxis=dict(categoryorder='total ascending', showgrid=False), plot_bgcolor='white')
            st.plotly_chart(fig_bar, use_container_width=True)
            with st.expander("상세 데이터 보기 (FWCI 포함)"): st.dataframe(top_partners_df.style.format({'Avg_FWCI': '{:.2f}'}))

        with tab_trend:
            st.info(f"**{target_country_name}**와(과) 주요 협력국 간의 연도별 협력 논문 수 추세를 개별 막대 차트로 보여줍니다.")
            min_year_trend = int(df['publication_year'].min()) if not df['publication_year'].empty else 2000
            max_year_trend = int(df['publication_year'].max()) if not df['publication_year'].empty else pd.Timestamp.now().year

            st.write("###### 분석할 연도 범위를 입력하세요:")
            col1_trend, col2_trend = st.columns(2)
            with col1_trend:
                default_start_year = max(min_year_trend, max_year_trend - 10)
                start_year_trend = st.number_input("시작 연도", min_value=min_year_trend, max_value=max_year_trend, value=default_start_year, key="trend_start_year")
            with col2_trend:
                end_year_trend = st.number_input("종료 연도", min_value=min_year_trend, max_value=max_year_trend, value=max_year_trend, key="trend_end_year")

            if start_year_trend > end_year_trend:
                st.error("시작 연도는 종료 연도보다 클 수 없습니다.")
            else:
                num_columns = 4
                cols = st.columns(num_columns)
                for i, partner_code in enumerate(top_partner_countries):
                    with cols[i % num_columns]:
                        partner_df = target_country_df[target_country_df['country_list'].apply(lambda x: partner_code in x)]
                        trend_data_p = partner_df.groupby('publication_year').size().reset_index(name='count')
                        trend_data_p = trend_data_p[(trend_data_p['publication_year'] >= start_year_trend) & (trend_data_p['publication_year'] <= end_year_trend)]

                        fig = px.bar(trend_data_p, x='publication_year', y='count', title=f'{get_country_name(partner_code)}')
                        fig.update_xaxes(range=[start_year_trend - 0.5, end_year_trend + 0.5], dtick=max(1, (end_year_trend - start_year_trend) // 5))
                        fig.update_traces(marker_color='#418cdc')
                        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None, yaxis_title=None, showlegend=False, height=250, bargap=0.3,
                                          title_font=dict(size=14, color='dimgray'))
                        st.plotly_chart(fig, use_container_width=True)

        with tab_matrix:
            st.markdown("주요 협력 국가들 **상호 간에** 얼마나 많이 협력하는지를 보여줍니다.<br>색상은 로그 스케일로 표현하여 값의 차이를 더 잘 보여줍니다.", unsafe_allow_html=True)
            network_countries = [target_country_code] + top_partner_countries
            def contains_any(lst): return any(c in lst for c in network_countries)
            network_df = df[df['country_list'].apply(contains_any)].copy()
            co_occurrence_list = []
            for countries in network_df['country_list']:
                filtered_countries = [c for c in countries if c in network_countries]
                if len(filtered_countries) > 1: co_occurrence_list.extend(list(combinations(sorted(filtered_countries), 2)))

            if co_occurrence_list:
                co_occurrence_counts = pd.Series(co_occurrence_list).value_counts().reset_index(name='count')
                co_occurrence_counts.columns = ['country_pair', 'count']
                co_occurrence_counts[['country1', 'country2']] = pd.DataFrame(co_occurrence_counts['country_pair'].tolist(), index=co_occurrence_counts.index)
                pivot_table = co_occurrence_counts.pivot_table(index='country1', columns='country2', values='count').fillna(0)
                all_pivot_data = pivot_table.T.add(pivot_table, fill_value=0)
                np.fill_diagonal(all_pivot_data.values, 0)
                log_heatmap_data = np.log10(all_pivot_data.replace(0, np.nan))
                text_data = all_pivot_data.replace(0, np.nan).applymap(lambda x: f'{x:.0f}' if pd.notna(x) else '')

                fig_matrix = go.Figure(data=go.Heatmap(z=log_heatmap_data, x=log_heatmap_data.columns, y=log_heatmap_data.index,
                                                     text=text_data, texttemplate="%{text}", hovertemplate='Y: %{y}<br>X: %{x}<br>협력 논문 수: %{text}<extra></extra>',
                                                     colorscale='Greens_r', colorbar=dict(title='협력 논문 수 (log)')))
                fig_matrix.update_layout(title='주요 국가 간 협력 네트워크 매트릭스 (로그 스케일)', xaxis_showgrid=False, yaxis_showgrid=False,
                                         xaxis_title="국가", yaxis_title="국가")
                st.plotly_chart(fig_matrix, use_container_width=True)
            else: st.warning("네트워크 매트릭스를 생성할 데이터가 충분하지 않습니다.")