# 파일 이름: main.py (전략 적용 후 수정된 버전)

import streamlit as st
import pandas as pd

# 각 탭의 render 함수를 import 합니다.
import tab_search
import tab_basic_dashboard
import tab_country_deepdive  # 나중에 수정할 것이므로 일단 주석 처리
import tab_deep_dashboard

# ==============================================================================
# ✨ 1. 상태(State) 초기화: 하나의 데이터 저장소와 하나의 액션 보관함으로 통합
# ==============================================================================
st.set_page_config(layout="wide")

def initialize_state():
    """앱 세션 상태를 초기화하는 함수"""
    # 데이터는 종류에 상관없이 하나의 변수에 저장
    if 'data' not in st.session_state:
        st.session_state.data = pd.DataFrame()
    # 현재 데이터의 종류를 나타내는 '타입' 변수
    if 'data_type' not in st.session_state:
        st.session_state.data_type = None  # 'search' 또는 'analysis'가 될 예정
    # 탭에서 올린 처리 대기 중인 '액션'
    if 'pending_action' not in st.session_state:
        st.session_state.pending_action = None

# 앱이 시작(또는 재로딩)될 때마다 상태 초기화 함수 실행
initialize_state()


# ==============================================================================
# ✨ 2. 중앙 액션 처리 로직: 모든 상태 변경은 여기서만!
# ==============================================================================
# 처리할 액션이 있는지 확인
if st.session_state.pending_action is not None:

    # 액션의 내용(종류, 데이터)을 꺼냄
    action_type, payload = st.session_state.pending_action

    if action_type == 'SEARCH_ACTION':
        # 검색 액션 처리
        st.session_state.data = payload
        st.session_state.data_type = 'search'
        st.toast("검색 완료! 검색 모드로 전환되었습니다.")

    elif action_type == 'UPLOAD_ACTION':
        # 업로드 액션 처리
        st.session_state.data = payload
        st.session_state.data_type = 'analysis'
        st.toast("파일 업로드 완료! 분석 모드로 전환되었습니다.")

    # 액션 처리가 끝났으므로, 보관함을 비워서 중복 실행 방지
    st.session_state.pending_action = None


# ==============================================================================
# 3. 메인 앱 UI 렌더링
# ==============================================================================

def render_home_tab():
    """홈 탭의 내용을 렌더링합니다. (이 함수는 변경 없음)"""
    st.header("🏠 시스템 안내")
    st.info("이 시스템은 논문 데이터를 수집하고 분석하는 기능을 제공합니다.")
    st.markdown("---")
    st.warning("""
    ### ※ 중요: 분석 기능 사용법
    이 시스템은 두 가지 모드로 작동합니다.
    - **검색 모드**: '논문 검색' 탭에서 검색을 실행한 상태입니다.
    - **분석 모드**: '기본 동향 분석' 탭 등에서 파일을 직접 업로드한 상태입니다.
    
    하나의 모드가 활성화되면 다른 모드의 데이터는 초기화됩니다.
    """)
    st.markdown("---")
    st.subheader("각 탭의 역할")
    st.markdown("""
    - **`🔍 논문 검색 및 수집`**: 새로운 데이터를 검색하고 **'검색 모드'**를 활성화합니다.
    - **`📊 기본 동향 분석` 등**: 파일을 업로드하여 **'분석 모드'**를 활성화하고, 해당 데이터를 분석합니다.
    """)

st.title("📚 논문 분석 시스템")

# 탭 UI 구성 (우선 두 탭에만 집중)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 홈",
    "🔍 논문 검색 및 수집",
    "📊 기본 동향 분석",
    "🔬 국가별 심층 분석",
    "✨ 키워드 동향 분석"
])

with tab1:
    render_home_tab()

with tab2:
    # ✨ 검색 탭에는 아무 인자도 전달할 필요가 없음.
    #    (액션 등록은 탭 내부에서 st.session_state를 통해 직접 하기 때문)
    tab_search.render()

with tab3:
    # ✨ 분석 탭에는 현재 '데이터'와 '데이터 타입'을 인자로 전달하여
    #    화면을 어떻게 그릴지 결정하게 함.
    tab_basic_dashboard.render(st.session_state.data, st.session_state.data_type)

with tab4:
    tab_country_deepdive.render(st.session_state.data, st.session_state.data_type)

with tab5:
    tab_deep_dashboard.render(st.session_state.data, st.session_state.data_type)