import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# 1. 读取数据
def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            c_db = json.load(f)
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            m_db = json.load(f)
        return c_db, m_db
    except Exception as e:
        st.error(f"文件读取失败，请检查 data 文件夹: {e}")
        return None, None

cpu_data, mb_data = load_data()

if cpu_data and mb_data:
    # 2. 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
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
            
            # 确定 CPU 价格
            t_p = selected_cpu.get("tray_price", 0)
            b_p = selected_cpu.get("boxed_price", 0)
            cpu_p = t_p if (t_p and str(t_p) != "缺货") else b_p
            if cpu_p: st.metric("CPU 参考价", f"￥{cpu_p}")

        with col2:
            st.subheader("🔌 推荐主板搭配")
            mb_hint = selected_cpu.get("supported_motherboards", "")
            
            # --- 核心改进：超级匹配逻辑 ---
            match_mb = None
            if mb_hint:
                # 提取关键词，比如 "H110系列" -> "H110"
                clean_hint = mb_hint.replace("系列", "").split('/')[0]
                for m in mb_data.get("Motherboard_Series", []):
                    # 只要主板库里的名字包含了 CPU 里的关键字，就匹配
                    if clean_hint in m["series"]:
                        match_mb = m
                        break

            if match_mb:
                st.success(f"**适配系列:** {match_mb['series']}")
                st.metric("主板参考价", f"￥{match_mb['reference_price']}")
                if "note" in match_mb: st.caption(match_mb["note"])
                
                # 计算总价
                if cpu_p and isinstance(cpu_p, (int, float)):
                    total = cpu_p + match_mb['reference_price']
                    st.markdown(f"### 💰 套装合计: `￥{total}`")
            else:
                # 如果还是匹配不到，至少把 CPU 推荐的文字显示出来
                st.warning(f"主板库暂未录入 {mb_hint} 的价格")
                st.write(f"建议搭配: {mb_hint}")
else:
    st.info("正在等待 GitHub 上的 .json 文件同步...")
