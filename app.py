import streamlit as st
import json
import re

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统")

# 1. 读取数据
def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            c_db = json.load(f)  # 如果这里崩溃，就是 cpus.json
        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            m_db = json.load(f)  # 如果这里崩溃，就是 motherboards.json
        return c_db, m_db
    except Exception as e:
        st.error(f"加载失败: {e}")
        return None, None

cpu_data, mb_data = load_data()

if cpu_data and mb_data:
    # 2. 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
    
    # 自动识别 JSON 键名
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
            
            # 价格提取逻辑
            cpu_p = selected_cpu.get("tray_price", 0) or selected_cpu.get("boxed_price", 0)
            if cpu_p and str(cpu_p) != "缺货":
                st.metric("CPU 参考价", f"￥{cpu_p}")

        with col2:
            st.subheader("🔌 推荐主板搭配")
            
            # --- 整合版匹配逻辑 ---
            match_mb = None
            
            # A. 获取基础 Hint (如 "H81/B85")
            hint = selected_cpu.get("supported_motherboards", "").upper()
            
            # B. 提取型号中的核心数字进行辅助判定 (如 "R7 5700G" -> "5700")
            model_digits = "".join(re.findall(r'\d+', selected_model))
            
            # C. 构造搜索关键词列表 (Search Tags)
            search_tags = []
            if hint:
                search_tags.append(hint.split('/')[0].replace("系列", ""))
            
            # D. AMD 自动补全逻辑 (针对 5000/7000 系列关键词)
            if brand == "AMD":
                if any(x in model_digits for x in ["5500", "5600", "5700", "5800", "5900", "5000"]):
                    search_tags.append("AM4")
                elif any(x in model_digits for x in ["7500", "7600", "7700", "7800", "8000", "9000"]):
                    search_tags.append("AM5")
            
            # E. 在主板库中循环寻找匹配项
            for m in mb_data.get("Motherboard_Series", []):
                m_name = m["series"].upper()
                m_socket = m.get("socket", "").upper()
                
                # 只要任何一个标签撞上了主板的名字或插槽名，即视为匹配
                if any(tag in m_name or tag in m_socket for tag in search_tags if tag):
                    match_mb = m
                    break

            # 4. 显示匹配结果
            if match_mb:
                st.success(f"**适配系列:** {match_mb['series']}")
                st.metric("主板参考价", f"￥{match_mb['reference_price']}")
                
                # 计算套装总价 (需确保价格为数值)
                try:
                    price_val = float(cpu_p) if cpu_p and str(cpu_p) != "缺货" else 0
                    if price_val > 0:
                        total = price_val + match_mb['reference_price']
                        st.markdown(f"### 💰 套装合计: `￥{total}`")
                except:
                    pass
            else:
                st.warning(f"暂无匹配主板数据 (搜索词: {', '.join(search_tags)})")

# 侧边栏提示
st.sidebar.markdown("---")
st.sidebar.caption("💡 提示：主板价格为该系列入门级参考价。")
st.sidebar.caption("数据来源：每日店面最新报价单")
