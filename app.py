import streamlit as st
import json

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            c_db = json.load(f)
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            m_db = json.load(f)
        return c_db, m_db
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None, None

cpu_data, mb_data = load_data()

if cpu_data and mb_data:
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
    # 兼容两种可能的键名
    k = ("Intel_Processors" if "Intel_Processors" in cpu_data else "Intel_Platform") if brand == "Intel" else ("AMD_Processors" if "AMD_Processors" in cpu_data else "AMD_Platform")
    cpus = cpu_data.get(k, [])

    selected_model = st.selectbox("选择处理器型号", [c["model"] for c in cpus])
    selected_cpu = next((item for item in cpus if item["model"] == selected_model), None)

    if selected_cpu:
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 处理器详情")
            st.write(f"**型号:** {selected_cpu['model']}")
            st.info(f"规格: {selected_cpu.get('specs', '暂无')}")
            # 价格计算
            cpu_p = selected_cpu.get("tray_price", 0) or selected_cpu.get("boxed_price", 0)
            if cpu_p and str(cpu_p) != "缺货":
                st.metric("CPU 参考价", f"￥{cpu_p}")

        with col2:
            st.subheader("🔌 推荐主板搭配")
            # --- 核心改进：AMD 自动识别 ---
            mb_hint = selected_cpu.get("supported_motherboards", "")
            
            # 如果是 AMD 且 JSON 没写主板，根据型号自动赋值
            if brand == "AMD" and not mb_hint:
                if "5000" in selected_model or "5600" in selected_model or "5700" in selected_model:
                    mb_hint = "AM4"
                elif "7000" in selected_model or "9000" in selected_model or "7800" in selected_model:
                    mb_hint = "AM5"

            match_mb = None
            if mb_hint:
                # 模糊匹配：只要主板库里的 series 包含关键字（如 AM4, AM5, H110）
                keyword = mb_hint.split('/')[0].replace("系列", "")
                for m in mb_data.get("Motherboard_Series", []):
                    if keyword.upper() in m["series"].upper() or keyword.upper() in m.get("socket", "").upper():
                        match_mb = m
                        break

            if match_mb:
                st.success(f"**适配系列:** {match_mb['series']}")
                st.metric("主板参考价", f"￥{match_mb['reference_price']}")
                
                # 计算总价
                if cpu_p and isinstance(cpu_p, (int, float)):
                    total = cpu_p + match_mb['reference_price']
                    st.markdown(f"### 💰 套装合计: `￥{total}`")
            else:
                st.warning("暂无匹配的主板报价")
