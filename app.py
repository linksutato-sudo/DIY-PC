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
    k = "Intel_Processors" if brand == "Intel" else "AMD_Processors"
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
            cpu_p = selected_cpu.get("tray_price", 0) or selected_cpu.get("boxed_price", 0)
            if cpu_p and str(cpu_p) != "缺货":
                st.metric("CPU 参考价", f"￥{cpu_p}")

        with col2:
            st.subheader("🔌 推荐主板搭配")
            mb_hint = selected_cpu.get("supported_motherboards", "")
            
            # --- 强化版模糊匹配逻辑 ---
            match_mb = None
            
            # 1. 尝试从 CPU 的 hint 里找 (如 H110, B550)
            search_tags = []
            if mb_hint:
                search_tags.append(mb_hint.split('/')[0].replace("系列", ""))
            
            # 2. 如果是 AMD，根据 CPU 型号名强行添加搜索词
            if brand == "AMD":
                if any(x in selected_model for x in ["5500", "5600", "5700", "5000"]):
                    search_tags.append("AM4")
                if any(x in selected_model for x in ["7000", "9000", "7800", "9800", "AM5"]):
                    search_tags.append("AM5")
            
            # 3. 开始在主板库匹配
            if search_tags:
                for m in mb_data.get("Motherboard_Series", []):
                    # 检查 tag 是否在主板系列名或插槽类型里
                    if any(tag.upper() in m["series"].upper() or tag.upper() in m.get("socket", "").upper() for tag in search_tags):
                        match_mb = m
                        break

            if match_mb:
                st.success(f"**适配系列:** {match_mb['series']}")
                st.metric("主板参考价", f"￥{match_mb['reference_price']}")
                if cpu_p and isinstance(cpu_p, (int, float)):
                    st.markdown(f"### 💰 套装合计: `￥{cpu_p + match_mb['reference_price']}`")
            else:
                st.warning("暂无自动匹配的主板报价")
