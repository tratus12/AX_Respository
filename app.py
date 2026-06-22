import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import datetime

# 페이지 기본 설정
st.set_page_config(
    page_title="팀 예산 관리 대시보드 Pro",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. API 주소(Web App URL) 설정 및 연결 체크
# -----------------------------------------------------------------------------
# Streamlit secrets 또는 세션 스테이트에서 URL 가져오기
WEB_APP_URL = st.secrets.get("web_app_url", "")

# 세션 스테이트를 통한 실시간 URL 입력 지원 (설정 편의성 제공)
if "temp_url" not in st.session_state:
    st.session_state["temp_url"] = WEB_APP_URL

# -----------------------------------------------------------------------------
# 2. 데이터 통신 헬퍼 함수 정의 (API Requests)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=5) # 5초간 캐싱하여 빠른 화면 전환 제공, 실시간성 유지
def fetch_all_data(url):
    """구글 앱스 스크립트 웹 앱에서 전체 예산 내역과 예산 한도를 가져옵니다."""
    if not url:
        return None
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"⚠️ API 호출 실패 (HTTP {response.status_code})")
    except Exception as e:
        st.error(f"⚠️ 연결 실패: {str(e)}")
    return None

def send_api_post(url, payload):
    """구글 앱스 스크립트 웹 앱으로 데이터를 전송(추가/삭제/설정 변경)합니다."""
    if not url:
        return False
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            return res_json.get("status") == "success"
    except Exception as e:
        st.error(f"⚠️ 요청 전송 실패: {str(e)}")
    return False

# -----------------------------------------------------------------------------
# 3. UI 및 연결 상태 가이드 구성
# -----------------------------------------------------------------------------
active_url = st.session_state["temp_url"]

if not active_url:
    st.title("📊 팀 예산 관리 시스템")
    st.warning("🔌 구글 앱스 스크립트 Web App URL 설정이 필요합니다!")
    
    st.markdown("""
    ### ⚙️ 대시보드를 구글 스프레드시트와 동기화하는 초간단 3단계:
    
    1. **앱스 스크립트 배포하기**
       * 구글 스프레드시트(`확장 프로그램 > Apps Script`)에 제공된 `README.md` 내 배포용 코드를 붙여넣습니다.
       * 우측 상단 **[배포 > 새 배포]**를 누른 뒤, 유형을 **'웹 앱'**으로 선택합니다.
       * **액세스 권한이 있는 사용자**를 반드시 **'모든 사용자(Anyone)'**로 설정 후 배포합니다.
    
    2. **URL 복사 및 입력**
       * 생성된 `웹 앱 URL`(https://script.google.com/macros/s/.../exec)을 아래 칸에 입력해 주세요.
    """)
    
    # 실시간 URL 입력을 위한 폼
    input_url = st.text_input("🔗 복사한 Web App URL을 여기에 붙여넣으세요:", value="")
    if st.button("연결 테스트 및 저장"):
        if input_url.startswith("https://script.google.com/"):
            st.session_state["temp_url"] = input_url
            st.success("🎉 URL이 임시 등록되었습니다! 페이지를 다시 로드합니다.")
            st.rerun()
        else:
            st.error("올바른 구글 웹 앱 주소 형식이 아닙니다.")
            
    st.markdown("""
    ---
    💡 **영구 적용하기:** 배포한 뒤 스트림릿 클라우드 대시보드의 **Settings > Secrets**에 아래 한 줄만 입력하면 접속할 때마다 자동으로 연결됩니다.
    ```toml
    web_app_url = "여러분의_웹앱_실제_주소"
    ```
    """)
    st.stop()

# API 통신 시도 및 데이터 로드
api_response = fetch_all_data(active_url)

if api_response is None:
    st.title("📊 팀 예산 관리 시스템")
    st.error("❌ 구글 앱스 스크립트가 올바른 JSON 데이터를 반환하지 않았습니다.")
    st.info("💡 스프레드시트의 Apps Script가 올바르게 배포되었는지, 그리고 URL의 액세스 권한이 '모든 사용자(Anyone)'로 되어 있는지 확인해 주세요.")
    if st.button("🔗 다른 URL 입력하기"):
        st.session_state["temp_url"] = ""
        st.rerun()
    st.stop()

# 정상 로드 시 변수 파싱
raw_data = api_response.get("data", [])
budget_limit = api_response.get("budget_limit", 10000000)

# DataFrame 구축 및 타입 정리
if raw_data:
    df = pd.DataFrame(raw_data)
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0).astype(int)
    
    # 신규 기능: 스프레드시트 컬럼에 비고(Description) 데이터가 누락된 경우를 위한 방어 코드
    if "Description" not in df.columns:
        df["Description"] = ""
    else:
        df["Description"] = df["Description"].fillna("")
else:
    df = pd.DataFrame(columns=["ID", "Month", "Member", "Category", "Amount", "Description"])

# --- 정상 연결 시 대시보드 메인 화면 로드 ---
st.title("📊 팀 예산 관리 시스템 Pro (Google Sheets)")
st.caption("실시간 클라우드 동기화 및 상세 내역 추적 지원 대시보드")

# 사이드바 설정 영역
st.sidebar.header("🎯 목표 예산 설정")
new_limit = st.sidebar.number_input(
    "이달의 목표 예산 한도 (원)",
    value=budget_limit,
    step=500000,
    format="%d"
)
if new_limit != budget_limit:
    payload = {"action": "update_limit", "value": int(new_limit)}
    if send_api_post(active_url, payload):
        st.sidebar.success("🎯 목표 예산이 실시간 업데이트되었습니다!")
        st.cache_data.clear() # 캐시 클리어 후 리로드
        st.rerun()

# 탭 구조 정의
tab_input, tab_dashboard = st.tabs(["📝 데이터 입력 및 관리", "📈 실시간 대시보드"])

# --- TAB 1: 데이터 입력 및 관리 ---
with tab_input:
    col_form, col_list = st.columns([1, 2])
    
    with col_form:
        st.subheader("새 예산 내역 입력")
        with st.form("budget_input_form", clear_on_submit=True):
            member = st.selectbox("팀원 선택", ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"])
            month_date = st.date_input("해당 월 선택", datetime.date.today())
            month_str = month_date.strftime("%Y-%m")
            
            category = st.selectbox("예산 항목", ["수선유지비", "비품", "개량공사", "소모품비", "회의비", "기타"])
            amount = st.number_input("사용 금액 (원)", min_value=0, step=1000, format="%d")
            
            # [신규 추가] 상세 내역(비고/적요) 기입 필드
            description = st.text_input("상세 사용 내역 (비고)", placeholder="예: 소모성 마우스 5개 구입, 지붕 보수 등")
            
            submit_btn = st.form_submit_button("기록 저장하기")
            
            if submit_btn:
                if amount <= 0:
                    st.warning("사용 금액은 0원보다 커야 합니다.")
                else:
                    new_id = str(int(datetime.datetime.now().timestamp() * 1000))
                    payload = {
                        "action": "add",
                        "id": new_id,
                        "month": month_str,
                        "member": member,
                        "category": category,
                        "amount": int(amount),
                        "description": description # 신규 필드 데이터 전송
                    }
                    if send_api_post(active_url, payload):
                        st.success(f"데이터가 구글 시트에 안전하게 기록되었습니다! (연월: {month_str})")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("스프레드시트에 데이터를 쓰는 데 실패했습니다.")

    with col_list:
        st.subheader("📂 입력 내역 관리")
        
        if df.empty:
            st.info("현재 입력된 예산 내역이 없습니다. 왼쪽 양식에서 추가해 주세요.")
        else:
            # 실시간 필터 적용
            st.write("🔍 데이터 필터링 및 다운로드")
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                all_months = ["전체"] + sorted(df["Month"].unique().tolist(), reverse=True)
                sel_month = st.selectbox("월별 필터", all_months)
            with f_col2:
                all_members = ["전체"] + sorted(df["Member"].unique().tolist())
                sel_member = st.selectbox("팀원 필터", all_members)
            with f_col3:
                all_cats = ["전체"] + sorted(df["Category"].unique().tolist())
                sel_cat = st.selectbox("항목 필터", all_cats)
                
            # 필터 쿼리 실행
            filtered_df = df.copy()
            if sel_month != "전체":
                filtered_df = filtered_df[filtered_df["Month"] == sel_month]
            if sel_member != "전체":
                filtered_df = filtered_df[filtered_df["Member"] == sel_member]
            if sel_cat != "전체":
                filtered_df = filtered_df[filtered_df["Category"] == sel_cat]
                
            # 데이터 그리드 렌더링 (비고 컬럼 순서 조정 및 노출)
            display_cols = ["Month", "Member", "Category", "Amount", "Description"]
            # 실존하는 열만 필터링하여 출력 오류 방지
            active_cols = [c for c in display_cols if c in filtered_df.columns]
            
            st.dataframe(
                filtered_df[active_cols].style.format({"Amount": "{:,.0f}원"}),
                use_container_width=True,
                hide_index=True
            )
            
            # [신규 기능] 필터링된 결과 데이터 CSV 내보내기 버튼 추가
            csv_data = filtered_df[active_cols].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 현재 필터링된 결과 내보내기 (Excel/CSV)",
                data=csv_data,
                file_name=f"team_budget_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_csv"
            )
            
            # 행 개별 삭제 기능 구현
            st.markdown("---")
            st.subheader("🗑️ 개별 내역 삭제")
            if not filtered_df.empty:
                delete_options = {
                    f"[{row['Month']}] {row['Member']} - {row['Category']} ({row['Amount']:,}원) - {row.get('Description', '')}": row['ID']
                    for idx, row in filtered_df.iterrows()
                }
                selected_to_delete = st.selectbox("삭제할 항목을 선택하세요", list(delete_options.keys()))
                
                if st.button("선택한 항목 삭제", type="primary"):
                    target_id = delete_options[selected_to_delete]
                    payload = {
                        "action": "delete",
                        "id": target_id
                    }
                    if send_api_post(active_url, payload):
                        st.success("데이터가 구글 시트에서 즉시 삭제되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("데이터 삭제 처리에 실패했습니다.")

# --- TAB 2: 실시간 대시보드 ---
with tab_dashboard:
    if df.empty:
        st.info("분석할 예산 데이터가 부족합니다. 먼저 '데이터 입력' 탭에서 데이터를 입력해 주세요.")
    else:
        total_spent = df["Amount"].sum()
        execution_rate = (total_spent / budget_limit) * 100
        remaining_budget = budget_limit - total_spent
        
        # [신규 추가] 예산 한도 상태 경고 및 진단 로직 (Smart Alert)
        if execution_rate > 100:
            st.error(f"🚨 **주의: 예산 한도를 초과했습니다!** 현재 한도 대비 {-remaining_budget:,.0f}원 초과 지출 중입니다.")
        elif execution_rate >= 85:
            st.warning(f"⚠️ **위험 경보: 예산 소진 임박!** 현재 집행률이 {execution_rate:.1f}%에 도달하였습니다. 남은 예산: {remaining_budget:,.0f}원")
        else:
            st.success(f"✅ **안전 상태:** 안정적인 예산 상황입니다. 남은 사용 가능 금액: {remaining_budget:,.0f}원")
        
        # 1. 상단 KPI 카드 블록
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.metric(
                label="누적 사용 총액", 
                value=f"{total_spent:,.0f}원", 
                delta=f"남은 잔여 예산: {remaining_budget:,.0f}원"
            )
            progress_val = min(int(execution_rate), 100)
            st.progress(progress_val / 100)
            st.caption(f"목표 대비 예산 집행률: **{execution_rate:.1f}%**")
            
        with kpi_col2:
            cat_totals = df.groupby("Category")["Amount"].sum()
            if not cat_totals.empty:
                top_cat = cat_totals.idxmax()
                top_cat_val = cat_totals.max()
                st.metric(label="최다 지출 항목", value=top_cat, delta=f"{top_cat_val:,.0f}원 누적")
            else:
                st.metric(label="최다 지출 항목", value="-")
                
        with kpi_col3:
            # [신규 추가] 건당 평균 지출액 분석 카드
            avg_amount = df["Amount"].mean()
            st.metric(
                label="건당 평균 사용액", 
                value=f"{avg_amount:,.0f}원", 
                delta=f"최대 지출: {df['Amount'].max():,.0f}원"
            )

        st.markdown("---")

        # 2. [신규 추가] 월별 지출 트렌드 라인 차트 영역
        st.subheader("📅 월별 총 지출액 추이 분석")
        monthly_trend = df.groupby("Month")["Amount"].sum().reset_index().sort_values("Month")
        
        fig_trend = px.line(
            monthly_trend,
            x="Month",
            y="Amount",
            markers=True,
            text="Amount",
            labels={"Amount": "총 사용액(원)", "Month": "기준월"},
            title="연간 지출 증감 트렌드 (설정 예산 한도 대비 흐름)",
            color_discrete_sequence=["#2563eb"]
        )
        fig_trend.update_traces(textposition="top center", texttemplate="%{y:,.0f}원")
        
        # 예산 한도 기준선 추가 (레드 가이드라인)
        fig_trend.add_hline(
            y=budget_limit, 
            line_dash="dash", 
            line_color="#ef4444", 
            annotation_text=f"목표 예산 한도 ({budget_limit:,.0f}원)", 
            annotation_position="top left"
        )
        fig_trend.update_layout(
            yaxis_gridcolor='rgba(200, 200, 200, 0.2)',
            margin=dict(t=50, b=20, l=20, r=20),
            height=350
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("---")

        # 3. 시각화 차트 영역 (좌/우 분할 레이아웃)
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("🏠 항목별 예산 분포 비율")
            fig_pie = px.pie(
                df, 
                values="Amount", 
                names="Category", 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with chart_col2:
            st.subheader("👥 팀원별 누적 사용액 비교")
            member_totals = df.groupby("Member")["Amount"].sum().reset_index()
            fig_bar = px.bar(
                member_totals,
                x="Member",
                y="Amount",
                text_auto=',.0f',
                labels={"Amount": "누적 금액 (원)", "Member": "팀원"},
                color_discrete_sequence=["#60a5fa"]
            )
            fig_bar.update_layout(yaxis_gridcolor='rgba(200, 200, 200, 0.2)', margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # 4. 월별/항목별 요약 피вут 테이블 (취합본)
        st.subheader("📊 월별 / 항목별 요약 취합 매트릭스")
        try:
            pivot_df = df.pivot_table(
                index="Month",
                columns="Category",
                values="Amount",
                aggfunc="sum",
                fill_value=0
            )
            pivot_df["합계"] = pivot_df.sum(axis=1)
            pivot_df = pivot_df.sort_index(ascending=False)
            
            st.dataframe(
                pivot_df.style.format("{:,.0f}원"),
                use_container_width=True
            )
        except Exception as e:
            st.warning("요약 테이블 생성 도중 에러가 발생했습니다. 입력 데이터 형식을 확인해 주세요.")
