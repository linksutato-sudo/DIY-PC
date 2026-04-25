import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# 1. 尝试读取两个数据库
try:
    with open('data/cpus.json', 'r', encoding='utf-8') as f:
        cpu_data = json.load(f)
    with open('data/motherboards.json', 'r', encoding='utf-8') as f:
        mb_data = json.load(f)
except FileNotFoundError:
    st.error("❌ 找不到数据文件！请确保 data 文件夹下有 cpus.json 和 motherboards.json")
    st.stop()

# 2. 平台选择逻辑
brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
# 自动兼容你 JSON 里的键名
intel_key = "Intel_Processors" if "Intel_Processors" in cpu_data else "Intel_Platform"
amd_key = "AMD_Processors" if "AMD_Processors" in cpu_data else "AMD_Platform"

cpus = cpu_data.get(intel_key if brand == "Intel" else amd_key, [])

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
        
        # 提取 CPU 价格
        t_price = selected_cpu.get("tray_price")
        b_price = selected_cpu.get("boxed_price")
        cpu_final_price = 0
        
        if t_price and str(t_price) != "缺货":
            st.metric("散片行情价", f"￥{t_price}")
            cpu_final_price = t_price
        elif b_price:
            st.metric("盒装参考价", f"￥{b_price}")
            cpu_final_price = b_price

    with col2:
        st.subheader("🔌 推荐主板搭配")
        # 获取该 CPU 推荐的主板关键字 (如 "H81/B85")
        mb_hint = selected_cpu.get("supported_motherboards", "")
        
        # 匹配逻辑：在主板库中寻找名称包含关键字的条目
        match_mb = None
        if mb_hint:
            # 取第一个关键字进行模糊匹配
            keyword = mb_hint.split('/')[0].split('系列')[0]
            match_mb = next((m for m in mb_data.get("Motherboard_Series", []) if keyword in m["series"]), None)

        if match_mb:
            st.success(f"**适配系列:** {match_mb['series']}")
            st.metric("主板参考价", f"￥{match_mb['reference_price']}")
            st.write(f"💡 {match_mb.get('note', '')}")
            
            # 自动计算板U套装总价
            if cpu_final_price > 0:
                total = cpu_final_price + match_mb['reference_price']
                st.markdown(f"### 💰 套装预估: `￥{total}`")
        else:
            st.warning(f"⚠️ 暂无 {mb_hint} 的主板报价数据")
