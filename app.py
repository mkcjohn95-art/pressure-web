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
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
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

# 关键事件清单
events = {
    "2025-11-23: 3#一开钻进": "2025-11-23",
    "2025-11-26: 移至4#": "2025-11-26",
    "2025-12-19: 4#移至5#": "2025-12-19",
    "2026-01-09: 5#移至3#": "2026-01-09",
    "2026-01-23: 3#移至7#": "2026-01-23",
    "2026-01-23: 7#移至6#": "2026-01-23",
    "2026-02-13: 7#遇起钻最高摩阻38t": "2026-02-13",
    "2026-03-02: 6#二开钻进": "2026-03-02",
    "2026-03-12: 6#二开钻进": "2026-03-12",
    "2026-04-13: 4#三开钻进": "2026-04-13",
    "2026-05-24: #三开钻进": "2026-05-24"
}

# 增加选择器
col1, col2 = st.columns([1, 2])
with col1:
    selected_event = st.selectbox("快速定位关键节点:", options=["显示全部"] + list(events.keys()))
with col2:
    selected_nodes = st.multiselect("选择监测节点 (可多选):", options=edited_df.index.tolist(), default=edited_df.index.tolist()[:3])

if selected_nodes:
    try:
        plot_df = edited_df.loc[selected_nodes].T
        plot_df.index = pd.to_datetime(plot_df.index, errors='coerce')
        plot_df = plot_df.sort_index()

        fig = go.Figure()
        symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'star', 'hexagon']

        for i, node in enumerate(selected_nodes):
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[node], 
                mode='lines+markers', name=str(node),
                marker=dict(symbol=symbols[i % len(symbols)], size=10),
                hovertemplate="<b>日期</b>: %{x|%Y-%m-%d}<br>" +
                              "<b>节点</b>: %{fullData.name}<br>" +
                              "<b>压力值</b>: %{y:.2f} kPa<extra></extra>"
            ))

        # 动态视角聚焦逻辑
        xaxis_config = dict(tickformat="%m-%d", type="date", gridcolor='lightgray')
        if selected_event != "显示全部":
            target_date = pd.to_datetime(events[selected_event])
            xaxis_config["range"] = [target_date - timedelta(days=7), target_date + timedelta(days=7)]

        fig.update_layout(
            xaxis=xaxis_config,
            yaxis=dict(title="压力值 (kPa)", gridcolor='lightgray'),
            plot_bgcolor='white', height=500,
            hovermode="closest"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("图表渲染中...")
else:
    st.info("请在上方选择框中勾选节点以显示曲线。")
