import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
from datetime import timedelta

# 1. 连接 Google Sheets 的配置
def get_gspread_client():
    # 使用你在 Secrets 里填写的配置
    creds_dict = st.secrets["gspread"]
    creds = Credentials.from_service_account_info(creds_dict)
    return gspread.authorize(creds)

# 2. 读取数据
def load_data():
    client = get_gspread_client()
    sheet = client.open("PressureData").sheet1
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    # 将“节点名称”设为索引
    df.set_index("节点名称", inplace=True)
    return df

# 3. 初始化界面
st.set_page_config(page_title="压力监测工作台", layout="wide")
st.title("📈 监测节点全景数据工作台")

# 读取并显示数据
if 'df' not in st.session_state:
    try:
        st.session_state.df = load_data()
    except Exception as e:
        st.error(f"无法读取数据，请检查表格名称是否为 PressureData: {e}")

# 4. 侧边栏管理
with st.sidebar:
    st.header("🔧 云端数据管理")
    if st.button("🔄 刷新最新数据"):
        st.session_state.df = load_data()
        st.rerun()
        
    st.divider()
    if st.button("💾 保存当前修改到云端"):
        client = get_gspread_client()
        sheet = client.open("PressureData").sheet1
        # 将 DataFrame 转为列表格式写入
        df_to_save = st.session_state.df.reset_index()
        sheet.clear()
        sheet.update([df_to_save.columns.values.tolist()] + df_to_save.values.tolist())
        st.success("数据已同步至 Google Sheets！")

# 5. 主编辑区
st.subheader("📝 监测数据表")
edited_df = st.data_editor(st.session_state.df, use_container_width=True)
st.session_state.df = edited_df

# 6. 图表逻辑 (保持原样)
# ... (这里放入你之前那段 plotly 画图的代码即可)
