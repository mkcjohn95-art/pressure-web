import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import timedelta

# --- 1. 配置区域 ---
# 替换这一行的 ID，例如: "1AbCdEfGhIjKlMnOpQrStUvWxYz"
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
    # 使用唯一 ID 直接访问，防止找不到表格
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    df.set_index("节点名称", inplace=True)
    return df

# --- 2. 页面初始化 ---
st.set_page_config(page_title="压力监测工作台", layout="wide")
st.title("📈 监测节点全景数据工作台")

if 'df' not in st.session_state:
    try:
        st.session_state.df = load_data()
        st.session_state.last_date = pd.to_datetime(st.session_state.df.columns[-1]).date()
    except Exception as e:
        st.error(f"连接 Google Sheets 失败，请检查表格 ID 和权限: {e}")
        # 兜底数据
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
    new_date = st.date_input("选择日期", value=st.session_state.last_date)
    if st.button("➕ 新增日期列"):
        st.session_state.df[str(new_date)] = 0.0
        st.session_state.last_date = new_date + timedelta(days=1)
        st.rerun()

    if st.button("💾 保存当前修改到云端"):
        try:
            client = get_gspread_client()
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1
            df_to_save = st.session_state.df.reset_index()
            sheet.clear()
            # 写入标题和数据
            sheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
            st.success("数据已同步至 Google Sheets！")
        except Exception as e:
            st.error(f"保存失败: {e}")

# --- 4. 主编辑区 ---
st.subheader("📝 监测数据表")
edited_df = st.data_editor(st.session_state.df, use_container_width=True, key="main_editor")
st.session_state.df = edited_df

# --- 5. 实时曲线图 ---
st.subheader("📊 实时曲线图")
try:
    plot_df = edited_df.T
    plot_df.index = pd.to_datetime(plot_df.index)
    plot_df = plot_df.sort_index()

    fig = go.Figure()
    symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up']

    for i, col in enumerate(plot_df.columns):
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[col], mode='lines+markers', name=str(col),
            marker=dict(symbol=symbols[i % len(symbols)], size=9)
        ))

    fig.update_layout(
        xaxis=dict(tickformat="%m-%d", type="date", gridcolor='lightgray'),
        yaxis=dict(title="压力值 (kPa)", gridcolor='lightgray'),
        plot_bgcolor='white', height=400
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.info("数据格式调整中，图表稍后显示...")
