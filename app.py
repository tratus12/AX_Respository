import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 페이지 기본 설정
st.set_page_config(
    page_title="팀 예산 관리 대시보드",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. 구글 스프레드시트 연결 설정 (Google Sheets API Connection)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_gspread_client():
    """Streamlit Secrets에 저장된 구글 서비스 계정 정보를 활용해 gspread 클라이언트를 인증합니다."""
    try:
        # 배포 환경 (Streamlit Secrets 사용)
        creds_info = st.secrets["gcp_service_account"]
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        # 로컬 개발 환경용 예외 처리 안내
        st.error("구글 서비스 계정 자격 증명(Secrets)을 찾을 수 없거나 올바르지 않습니다. 'README.md' 파일을 참고하여 설정을 완료해 주세요.")
        st.stop()

def get_google_sheet():
    """구글 시트를 열고 필요한 워크시트가 없으면 생성하여 반환합니다."""
    client = get_gspread_client()
    try:
        # 시트 이름은 임의로 'Team_Budget_DB'로 지정 (Secrets에서 동적으로 가져올 수도 있음)
        sheet_name = st.secrets.get("spreadsheet_name", "Team_Budget_DB")
        spreadsheet = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        st.error(f"구글 드라이브에서 '{sheet_name}' 이름의 스프레드시트를 찾을 수 없습니다. 서비스 계정 이메일에 공유를 완료했는지 확인해 주세요.")
        st.stop()
        
    # 'data' 워크시트 가져오기 또는 생성하기
    try:
        worksheet = spreadsheet.worksheet("data")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="data", rows="100", cols="20")
        # 헤더 삽입
        worksheet.append_row(["ID", "Month", "Member", "Category", "Amount"])
        
    # 'config' 워크시트(목표 예산 등 설정 저장용) 가져오기 또는 생성하기
    try:
        config_sheet = spreadsheet.worksheet("config")
    except gspread.WorksheetNotFound:
        config_sheet = spreadsheet.add_worksheet(title="config", rows="10", cols="5")
        config_sheet.append_row(["Key", "Value"])
        config_sheet.append_row(["budget_limit", "10000000"]) # 기본값 1천만 원
        
    return worksheet, config_sheet

# 구글 시트 객체 초기 로드
worksheet, config_sheet = get_google_sheet()

# -----------------------------------------------------------------------------
# 2. 데이터 헬퍼 함수 정의
# -----------------------------------------------------------------------------
def load_data():
    """스프레드시트에서 예산 내역 데이터를 판다스 DataFrame으로 가져옵니다."""
    records = worksheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=["ID", "Month", "Member", "Category", "Amount"])
    df = pd.DataFrame(records)
    # 데이터 타입 정렬
    df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce').fillna(0).astype(int)
    return df

def load_budget_limit():
    """스프레드시트 config 워크시트에서 목표 예산 설정을 읽어옵니다."""
    try:
        records = config_sheet.get_all_records()
        for r in records:
            if r["Key"] == "budget_limit":
                return int(r["Value"])
    except:
        pass
    return 10000000

def update_budget_limit_in_sheet(limit_val):
    """목표 예산 설정 값을 스프레드시트에 저장합니다."""
    try:
        cell = config_sheet.find("budget_limit")
        config_sheet.update_cell(cell.row, cell.col + 1, str(limit_val))
    except gspread.CellNotFound:
        config_sheet.append_row(["budget_limit", str(limit_val)])

# -----------------------------------------------------------------------------
# 3. UI 구성 요소 구현
# -----------------------------------------------------------------------------
st.title("📊 팀 예산 관리 시스템 (Google Sheets 연동)")
st.caption("부장님 보고용 월별 예산 실시간 취합 및 분석 대시보드")

# 사이드바 설정 영역
st.sidebar.header("🎯 목표 예산 설정")
current_limit = load_budget_limit()
new_limit = st.sidebar.number_input(
    "이달의 목표 예산 한도 (원)",
    value=current_limit,
    step=500000,
    format="%d"
)
if new_limit != current_limit:
    update_budget_limit_in_sheet(new_limit)
    st.sidebar.success("🎯 목표 예산이 실시간 업데이트되었습니다!")
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
            
            category = st.selectbox("예산 항목", ["수선유지비", "비품", "개량공사"])
            amount = st.number_input("사용 금액 (원)", min_value=0, step=1000, format="%d")
            
            submit_btn = st.form_submit_button("기록 저장하기")
            
            if submit_btn:
                if amount <= 0:
                    st.warning("사용 금액은 0원보다 커야 합니다.")
                else:
                    # 구글 시트에 행 추가
                    new_id = str(int(datetime.datetime.now().timestamp() * 1000))
                    worksheet.append_row([new_id, month_str, member, category, amount])
                    st.success(f"데이터가 구글 시트에 안전하게 기록되었습니다! (연월: {month_str})")
                    st.rerun()

    with col_list:
        st.subheader("📂 입력 내역 관리")
        df = load_data()
        
        if df.empty:
            st.info("현재 입력된 예산 내역이 없습니다. 왼쪽 양식에서 추가해 주세요.")
        else:
            # 실시간 필터 적용
            st.write("🔍 데이터 필터링")
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
                
            # 데이터 그리드 렌더링
            st.dataframe(
                filtered_df.style.format({"Amount": "{:,.0f}원"}),
                use_container_width=True,
                hide_index=True
            )
            
            # 행 개별 삭제 기능 구현
            st.markdown("---")
            st.subheader("🗑️ 개별 내역 삭제")
            if not filtered_df.empty:
                delete_options = {
                    f"[{row['Month']}] {row['Member']} - {row['Category']} ({row['Amount']:,}원)": row['ID']
                    for idx, row in filtered_df.iterrows()
                }
                selected_to_delete = st.selectbox("삭제할 항목을 선택하세요", list(delete_options.keys()))
                
                if st.button("선택한 항목 삭제", type="primary"):
                    target_id = delete_options[selected_to_delete]
                    try:
                        # 시트에서 ID 셀 검색하여 해당 행 삭제
                        cell = worksheet.find(str(target_id))
                        worksheet.delete_rows(cell.row)
                        st.success("데이터가 구글 시트에서 즉시 삭제되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error("데이터 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

# --- TAB 2: 실시간 대시보드 ---
with tab_dashboard:
    df = load_data()
    
    if df.empty:
        st.info("분석할 예산 데이터가 부족합니다. 먼저 '데이터 입력' 탭에서 데이터를 입력해 주세요.")
    else:
        total_spent = df["Amount"].sum()
        execution_rate = (total_spent / new_limit) * 100
        
        # 1. 상단 KPI 카드 블록
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.metric(
                label="누적 사용 총액", 
                value=f"{total_spent:,.0)원", 
                delta=f"한도 {new_limit:,.0f}원 대비"
            )
            # 진행 바 시각화
            progress_val = min(int(execution_rate), 100)
            st.progress(progress_val / 100)
            st.caption(f"목표 대비 예산 집행률: **{execution_rate:.1f}%**")
            
        with kpi_col2:
            # 가장 지출이 많은 항목 계산
            cat_totals = df.groupby("Category")["Amount"].sum()
            if not cat_totals.empty:
                top_cat = cat_totals.idxmax()
                top_cat_val = cat_totals.max()
                st.metric(label="최다 지출 항목", value=top_cat, delta=f"{top_cat_val:,.0f}원 누적")
            else:
                st.metric(label="최다 지출 항목", value="-")
                
        with kpi_col3:
            st.metric(label="등록 데이터 건수", value=f"{len(df)} 건", delta="구글 시트 연동 활성화")

        st.markdown("---")

        # 2. 시각화 차트 영역
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("🏠 항목별 예산 분포")
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
            st.subheader("👥 팀원별 누적 사용액")
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

        # 3. 월별/항목별 요약 피벗 테이블 (취합본)
        st.subheader("📅 월별/항목별 요약 취합 테이블")
        try:
            # 피벗 테이블 생성
            pivot_df = df.pivot_table(
                index="Month",
                columns="Category",
                values="Amount",
                aggfunc="sum",
                fill_value=0
            )
            # 행별 총합 추가
            pivot_df["합계"] = pivot_df.sum(axis=1)
            pivot_df = pivot_df.sort_index(ascending=False)
            
            st.dataframe(
                pivot_df.style.format("{:,.0f}원"),
                use_container_width=True
            )
        except Exception as e:
            st.warning("요약 테이블 생성 도중 에러가 발생했습니다. 입력 데이터 형식을 확인해 주세요.")
