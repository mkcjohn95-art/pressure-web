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
    try:
        st.session_state.df = load_data()
        st.session_state.last_date = pd.to_datetime(st.session_state.df.columns[-1], errors='coerce').date()
    except Exception as e:
        st.error(f"连接 Google Sheets 失败: {e}")
        st.session_state.df = pd.DataFrame({"2026-06-24": [0.0]}, index=["节点1"])
        st.session_state.last_date = pd.to_datetime("2026-06-24").date()

# --- 3. 侧边栏 ---
with st.sidebar:
    st.header("🔧 云端数据管理")
    if st.button("🔄 刷新最新数据"):
        try:
            st.session_state.df = load_data()
            st.rerun()
        except Exception as e:
            st.error("刷新失败")
    st.divider()
    new_date = st.date_input("日期选择", value=st.session_state.last_date)
    if st.button("➕ 新增日期列"):
        st.session_state.df[str(new_date)] = 0.0
        st.rerun()
    if st.button("💾 保存当前修改到云端"):
        try:
            client = get_gspread_client()
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1
            df_to_save = st.session_state.df.reset_index()
            sheet.clear()
            sheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
            st.success("数据已同步至云端！")
        except Exception as e:
            st.error(f"保存失败: {e}")

# --- 4. 主编辑区 ---
st.subheader("📝 监测数据表")
edited_df = st.data_editor(st.session_state.df, use_container_width=True, key="main_editor")
st.session_state.df = edited_df

# --- 5. 实时曲线图 ---
st.subheader("📊 实时曲线图")

event_list = [
    ("25.11.23: 3#一开钻进", "2025-11-23"), ("25.11.26: 移至4#", "2025-11-26"),
    ("25.12.19: 4#移至5#", "2025-12-19"), ("26.01.09: 5#移至3#", "2026-01-09"),
    ("26.01.23: 3#移至7#", "2026-01-23"), ("26.01.23: 7#移至6#", "2026-01-23"),
    ("26.02.13: 7#遇起钻最高摩阻38t", "2026-02-13"), ("26.03.02: 6#二开钻进", "2026-03-02"),
    ("26.03.12: 6#二开钻进", "2026-03-12"), ("26.04.13: 4#三开钻进", "2026-04-13"),
    ("26.05.24: #三开钻进", "2026-05-24")
]

options = ["显示全部", "取消所有竖线"] + [e[0] for e in event_list]

col1, col2 = st.columns([1, 2])
with col1:
    selected_event = st.selectbox("快速定位施工阶段:", options=options)
with col2:
    selected_nodes = st.multiselect("选择监测节点:", options=edited_df.index.tolist(), default=edited_df.index.tolist()[:3])

if selected_nodes:
    try:
        plot_df = edited_df.loc[selected_nodes].T
        plot_df.index = pd.to_datetime(plot_df.index, errors='coerce')
        plot_df = plot_df.sort_index()

        fig = go.Figure()
        symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'star', 'hexagon']

        # 1. 绘制曲线
        for i, node in enumerate(selected_nodes):
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[node], mode='lines+markers', name=str(node),
                marker=dict(symbol=symbols[i % len(symbols)], size=8),
                hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br><b>节点</b>: %{fullData.name}<br><b>压力值</b>: %{y:.2f} kPa<extra></extra>"
            ))

        # 2. 绘制竖线及悬停日期
        if selected_event != "取消所有竖线":
            for label, date_str in event_list:
                date_obj = pd.to_datetime(date_str)
                fig.add_vline(x=date_obj, line_dash="dash", line_color="gray", opacity=0.4)
                fig.add_trace(go.Scatter(
                    x=[date_obj], y=[0], mode='markers',
                    marker=dict(size=1, opacity=0),
                    hoverinfo='text',
                    text=f"<b>关键事件日期</b>: {date_str}<br>{label}",
                    showlegend=False
                ))

        # 3. 布局逻辑：只在特定施工阶段时进行强制范围聚焦
        xaxis_config = dict(tickformat="%m-%d", type="date", gridcolor='lightgray')
        
        # 核心改动：只有当选中具体某个施工阶段时，才限制 X 轴范围；
        # “显示全部”和“取消所有竖线”均交由 Plotly 自动调整，保持你图上的原始比例。
        if selected_event not in ["显示全部", "取消所有竖线"]:
            idx = next(i for i, v in enumerate(event_list) if v[0] == selected_event)
            start_date = pd.to_datetime(event_list[idx][1])
            end_date = pd.to_datetime(event_list[idx+1][1]) if idx < len(event_list) - 1 else start_date + timedelta(days=7)
            xaxis_config["range"] = [start_date, end_date]

        fig.update_layout(
            xaxis=xaxis_config, yaxis=dict(title="压力值 (kPa)"), 
            plot_bgcolor='white', height=500, hovermode="closest"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("数据渲染中...")
else:
    st.info("请在上方选择框中勾选节点以显示曲线。")
