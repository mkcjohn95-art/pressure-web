import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import timedelta

# --- 1. 配置区域 ---
SPREADSHEET_ID = "1W7VWIIWspuqTSCOGvKqJVP0lQjUS33zDi-KDJFe0Vkk"

def get_gspread_client():
    creds_dict = st.secrets["gspread"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_data():
    client = get_gspread_client()
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.set_index(df.columns[0], inplace=True)
    df.index.name = "节点名称"
    df.columns = [str(col) for col in df.columns]
    return df

# --- 2. 页面初始化 ---
st.set_page_config(page_title="压力监测工作台", layout="wide")
st.title("📈 监测节点全景数据工作台")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 3. 侧边栏 ---
with st.sidebar:
    st.header("🔧 云端数据管理")
    if st.button("🔄 刷新最新数据"):
        st.session_state.df = load_data()
        st.rerun()

# --- 4. 主编辑区 ---
st.subheader("📝 监测数据表")
st.session_state.df = st.data_editor(st.session_state.df, use_container_width=True)

# --- 5. 实时曲线图 ---
st.subheader("📊 实时曲线图")

event_list = [
    ("3#一开钻进", "2025-11-23"), ("移至4#", "2025-11-26"),
    ("4#移至5#", "2025-12-19"), ("5#移至3#", "2026-01-09"),
    ("3#移至7#", "2026-01-23"), ("7#移至6#", "2026-01-23"),
    ("7#遇起钻最高摩阻38t", "2026-02-13"), ("6#二开钻进", "2026-03-02"),
    ("6#二开钻进", "2026-03-12"), ("4#三开钻进", "2026-04-13"),
    ("#三开钻进", "2026-05-24")
]

options = ["显示全部", "取消所有竖线"] + [f"{e[1]} - {e[0]}" for e in event_list]
selected_event = st.selectbox("快速定位施工阶段:", options=options)
selected_nodes = st.multiselect("选择监测节点:", options=st.session_state.df.index.tolist(), default=st.session_state.df.index.tolist()[:1])

if selected_nodes:
    plot_df = st.session_state.df.loc[selected_nodes].T
    plot_df.index = pd.to_datetime(plot_df.index)
    plot_df = plot_df.sort_index()

    fig = go.Figure()

    # 绘制曲线
    for node in selected_nodes:
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[node], mode='lines+markers', name=str(node),
            hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br><b>压力值</b>: %{y:.2f} kPa<extra></extra>"
        ))

    # 绘制竖线与标注
    if selected_event != "取消所有竖线":
        for i, (event_name, date_str) in enumerate(event_list):
            date_val = pd.to_datetime(date_str)
            fig.add_vline(x=date_val, line_dash="dash", line_color="gray", opacity=0.4)
            
            # 使用奇偶判断，错开文字高度，彻底防止相邻文字重叠
            shift_top = 10 if i % 2 == 0 else 30
            shift_bottom = -10 if i % 2 == 0 else -30
            
            # 顶部日期 (加大、加黑)
            fig.add_annotation(
                x=date_val, y=1, yref="paper", text=date_str, 
                showarrow=False, font=dict(size=14, color="black", weight="bold"), 
                yshift=shift_top, xanchor="center", yanchor="bottom"
            )
            # 底部事件 (加大、加黑)
            fig.add_annotation(
                x=date_val, y=0, yref="paper", text=event_name, 
                showarrow=False, font=dict(size=14, color="black", weight="bold"), 
                yshift=shift_bottom, xanchor="center", yanchor="top"
            )

    # 范围缩放逻辑
    xaxis_range = None
    if selected_event not in ["显示全部", "取消所有竖线"]:
        target_date = pd.to_datetime(selected_event.split(" - ")[0])
        xaxis_range = [target_date - timedelta(days=3), target_date + timedelta(days=10)]

    fig.update_layout(
        xaxis=dict(
            range=xaxis_range, 
            gridcolor='lightgray',
            tickformat="%Y-%m-%d" # 强制 X 轴日期格式为你表格的格式，去除英文显示
        ),
        yaxis=dict(title="压力值 (kPa)"),
        plot_bgcolor='white', 
        height=600, 
        margin=dict(t=100, b=100) # 增大上下边距，给加大的文字留出足够空间
    )
    st.plotly_chart(fig, use_container_width=True)
