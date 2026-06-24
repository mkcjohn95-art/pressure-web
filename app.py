import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. 页面配置：宽屏显示
st.set_page_config(page_title="压力监测工作台", layout="wide")
st.title("📈 监测节点全景数据工作台")

# 2. 初始化数据逻辑
if 'df' not in st.session_state:
    # 默认构造示例数据：行=编号，列=日期
    st.session_state.df = pd.DataFrame(
        data={"2026-11-13": [45.7, 86.3, 54.3], "2026-11-14": [45.8, 84.5, 55.0]},
        index=["1号", "3号", "6号"]
    )

# 3. 侧边栏：管理结构 (日期列/节点行)
with st.sidebar:
    st.header("🔧 数据结构管理")

    # 日期管理
    new_date = st.date_input("选择日期")
    if st.button("➕ 新增日期列"):
        st.session_state.df[str(new_date)] = 0.0
        st.rerun()

    date_to_del = st.selectbox("选择要删除的日期", st.session_state.df.columns)
    if st.button("➖ 删除该日期列"):
        st.session_state.df.drop(columns=[date_to_del], inplace=True)
        st.rerun()

    st.divider()

    # 节点管理
    new_sensor = st.text_input("新增节点编号")
    if st.button("➕ 新增节点行"):
        st.session_state.df.loc[new_sensor] = 0.0
        st.rerun()

# 4. 主界面：可交互表格
st.subheader("📝 监测数据表")
st.info("💡 提示：在 Excel 复制数据，点选表格内单元格按 Ctrl+V 即可批量覆盖。")
edited_df = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic")
st.session_state.df = edited_df

# 5. 图表渲染：自动颜色与形状区分
st.subheader("📊 实时曲线图")
plot_df = edited_df.T
plot_df.index = pd.to_datetime(plot_df.index)
plot_df = plot_df.sort_index()

fig = go.Figure()
symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'pentagon']

for i, col in enumerate(plot_df.columns):
    symbol = symbols[i % len(symbols)]
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df[col], mode='lines+markers', name=str(col),
        marker=dict(symbol=symbol, size=9),
        line=dict(width=2.5),
        hovertemplate="日期: %{x|%Y-%m-%d}<br>编号: " + str(col) + "<br>数据: %{y} kPa<extra></extra>"
    ))

fig.update_layout(
    xaxis=dict(tickformat="%m-%d", type="date", gridcolor='lightgray'),
    yaxis=dict(title="压力值 (kPa)", gridcolor='lightgray'),
    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
    plot_bgcolor='white',
    height=600
)
st.plotly_chart(fig, use_container_width=True)

# 6. 保存功能
if st.button("💾 导出为 Excel"):
    edited_df.to_excel("压力监测数据_最新.xlsx")
    st.success("数据已成功保存至代码所在目录的『压力监测数据_最新.xlsx』！")