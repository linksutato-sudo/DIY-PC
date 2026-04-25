import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# 1. 确保数据文件安全读取
def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            cpu_data = json.load(f)
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            mb_data = json.load(f)
        return cpu_data, mb_data
    except FileNotFoundError:
        st.error("❌ 缺少数据文件！请检查 data/ 文件夹下是否有 cpus.json 和 motherboards.json")
        st.stop()

data, mb_data = load_data()

# 2. 平台与型号选择
brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
cpus = data["Intel_Processors"] if brand == "Intel" else data["AMD_Processors"]
selected_model = st.selectbox("选择处理器型号", [c["model"] for c in cpus])

# 3. 匹配选中的 CPU 数据
selected_cpu = next((item for item in cpus if item["model"] == selected_model), None)

if selected_cpu:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 处理器详情")
        st.write(f"**型号:** {selected_cpu['model']}")
        st.write(f"**规格:** {selected_cpu.get('specs', '暂无')}")
        
        # 价格展示
        price = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price")
        if price and price != "缺货":
            st.metric("参考行情价", f"￥{price}")

    with col2:
        st.subheader("🔌 推荐主板搭配")
        
        # --- 核心逻辑：从 CPU 规格或字段中寻找针脚信息进行匹配 ---
        # 优先读取 CPU 数据里的主板字段
        mb_hint = selected_cpu.get("supported_motherboards", "")
        
        # 如果需要从 mb_data 库中提取价格
        # 逻辑：查找主板库中兼容该 CPU 系列的条目
        match = next((m for m in mb_data["Motherboard_Series"] if m["series"].split('(')[0] in mb_hint), None)
        
        if match:
            st.success(f"**推荐系列:** {match['series']}")
            st.write(f"**芯片组:** {', '.join(match['chipsets'])}")
            st.metric("主板参考价", f"￥{match['reference_price']}")
        else:
            st.info(f"**建议搭配:** {mb_hint if mb_hint else '请核对接口'}")
