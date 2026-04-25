import streamlit as st
import json

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")

st.title("🖥️ DIY-PC 硬件导购系统")

# 读取数据
with open('data/cpus.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 简单的分类逻辑
brand = st.radio("选择平台", ["Intel", "AMD"])

if brand == "Intel":
    cpus = data["Intel_Processors"]
else:
    cpus = data["AMD_Processors"]

selected_cpu = st.selectbox("选择处理器型号", [c["model"] for c in cpus])

# 显示详情
for c in cpus:
    if c["model"] == selected_cpu:
        st.write(f"**规格:** {c.get('specs', '暂无')}")
        if "tray_price" in c:
            st.metric("散片价格", f"￥{c['tray_price']}")
        elif:
            st.metric("盒装价格", f"￥{c['boxed_price']}")
        
