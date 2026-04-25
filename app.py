import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# --- 1. 安全读取数据函数 ---
def load_all_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            c_data = json.load(f)
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            m_data = json.load(f)
        return c_data, m_data
    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        st.info("请检查 data 文件夹下是否有 cpus.json 和 motherboards.json")
        st.stop()

cpu_db, mb_db = load_all_data()

# --- 2. 平台选择 ---
# 自动检测 JSON 里的键名，防止 KeyError
intel_key = "Intel_Processors" if "Intel_Processors" in cpu_db else "Intel_Platform"
amd_key = "AMD_Processors" if "AMD_Processors" in cpu_db else "AMD_Platform"

brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
cpus = cpu_db.get(intel_key if brand == "Intel" else amd_key, [])

if not cpus:
    st.warning("JSON 库中未找到对应的处理器列表")
    st.stop()

# --- 3. 型号选择 ---
selected_model = st.selectbox("选择处理器型号", [c["model"] for c in cpus])
selected_cpu = next((item for item in cpus if item["model"] == selected_model), None)

if selected_cpu:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 处理器详情")
        st.write(f"**型号:** {selected_cpu['model']}")
        st.info(f"规格: {selected_cpu.get('specs', '暂无')}")
        
        # 价格逻辑
        t_price = selected_cpu.get("tray_price")
        b_price = selected_cpu.get("boxed_price")
        
        if t_price and str(t_price) != "缺货":
            st.metric("散片行情价", f"￥{t_price}")
        if b_price:
            st.metric("盒装参考价", f"￥{b_price}")

    with col2:
        st.subheader("🔌 推荐主板")
        # 获取 CPU 推荐的主板关键字 (比如 "H81/B85")
        mb_hint = selected_cpu.get("supported_motherboards", "")
        
        # 匹配主板价格逻辑
        match_mb = None
        if mb_hint:
            # 只要 CPU 里的关键字在主板系列的名称里，就认为匹配成功
            keyword = mb_hint.split('/')[0] 
            match_mb = next((m for m in mb_db.get("Motherboard_Series", []) if keyword in m["series"]), None)

        if match_mb:
            st.success(f"**建议搭配:** {match_mb['series']}")
            st.metric("主板参考价", f"￥{match_mb['reference_price']}")
            st.caption(f"适配芯片组: {', '.join(match_mb['chipsets'])}")
            
            # 计算总价
            cpu_p = t_price if (t_price and str(t_price) != "缺货") else b_price
            if cpu_p and isinstance(cpu_p, (int, float)):
                total = cpu_p + match_mb['reference_price']
                st.write("---")
                st.write(f"**💰 板 U 套装预估: ￥{total}**")
        else:
            st.warning(f"主板库中暂无 {mb_hint} 的详细报价")
