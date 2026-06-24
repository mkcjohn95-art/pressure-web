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
    # 强制将第一列设为索引，防止“节点名称”找不到报错
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
        st.error(f"连接 Google Sheets 失败，请检查表格 ID 和权限: {e}")
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
        st.rerun()

    if st.button("💾 保存当前修改到云端"):
        try:
            client = get_gspread_client()
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1
            df_to_save = st.session_state.df.reset_index()
            sheet.clear()
            sheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
            st.success("数据已同步至 Google Sheets！")
        except Exception as e:
            st.error(f"保存失败: {e}")

# --- 4. 主编辑区 ---
st.subheader("📝 监测数据表")
edited_df = st.data_editor(st.session_state.df, use_container_width=True, key="main_editor")
st.session_state.df = edited_df

# --- 5. 多选高亮曲线图 ---
st.subheader("📊 实时曲线图")

# 获取所有节点名称
all_nodes = edited_df.index.tolist()
# 提供多选框，默认选中前三个
selected_nodes = st.multiselect("选择要高亮的监测节点:", options=all_nodes, default=all_nodes[:3])

if selected_nodes:
    try:
        plot_df = edited_df.loc[selected_nodes].T
        # 处理日期索引转换
        plot_df.index = pd.to_datetime(plot_df.index, errors='coerce')
        plot_df = plot_df.sort_index()

        fig = go.Figure()
        for node in selected_nodes:
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[node], 
                mode='lines+markers', name=str(node),
                marker=dict(size=9)
            ))

        fig.update_layout(
            xaxis=dict(tickformat="%m-%d", type="date", gridcolor='lightgray'),
            yaxis=dict(title="压力值 (kPa)", gridcolor='lightgray'),
            plot_bgcolor='white', height=400,
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("数据格式调整中，图表稍后显示...")
else:
    st.info("请在上方选择框中勾选节点以显示曲线。")
