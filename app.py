import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# 1. 尝试读取两个数据库
def load_data():
    try:
        # 使用相对路径读取 data 文件夹下的文件
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            c_db = json.load(f)
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            m_db = json.load(f)
        return c_db, m_db
    except Exception as e:
        st.error(f"数据加载失败: {e}")
        return None, None

cpu_data, mb_data = load_data()

if cpu_data and mb_data:
    # 2. 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
    
    # 自动匹配 JSON 里的键名
    k = "Intel_Processors" if brand == "Intel" else "AMD_Processors"
    cpus = cpu_data.get(k, [])

    # 3. 选择型号
    selected_model = st.selectbox("选择处理器型号", [c["model"] for c in cpus])
    selected_cpu = next((item for item in cpus if item["model"] == selected_model), None)

    if selected_cpu:
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 处理器详情")
            st.write(f"**型号:** {selected_cpu['model']}")
            st.info(f"规格: {selected_cpu.get('specs', '暂无')}")
            
            # 价格
            t_p = selected_cpu.get("tray_price", 0)
            b_p = selected_cpu.get("boxed_price", 0)
            cpu_p = t_p if (t_p and str(t_p) != "缺货") else b_p
            
            if cpu_p:
                st.metric("CPU 参考价", f"￥{
