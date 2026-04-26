import streamlit as st
import json
import os

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

# 定义场景与 Tier、预算的关联
SCENARIOS = {
    "办公/家用 (Low/Entry)": {"min": 2000, "max": 4000, "tier": "Entry"},
    "主流网游 (Entry/Mid)": {"min": 4001, "max": 7000, "tier": "Mid"},
    "3A游戏/2K竞技 (Mid/High-Mid)": {"min": 7001, "max": 12000, "tier": "High-Mid"},
    "4K创作/深度学习 (High-Mid/Flagship)": {"min": 12001, "max": 25000, "tier": "Flagship"},
    "顶级发烧/生产力 (Flagship+)": {"min": 25001, "max": 99999, "tier": "Flagship"}
}
TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

def load_data():
    base_path = "data"
    files = {"cpus": "cpus.json", "gpus": "gpus.json", "memory": "memory_modules.json",
             "mb_models": "motherboard_models.json", "mb_series": "motherboards_series.json",
             "storage": "storage_devices.json"}
    data = {}
    for key, filename in files.items():
        path = os.path.join(base_path, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data[key] = json.load(f)
        except: data[key] = {}
    return data

def get_val(item, key, default=0):
    val = item.get(key, default)
    try: return float(val) if key == 'price' else val
    except: return 0

# --- 主程序 ---
def main():
    st.title("🖥️ DIY PC 场景化平衡配置专家")
    all_data = load_data()

    # --- 1. 预算与场景锁定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=100000, value=6500, step=500)
    
    # 根据预算自动识别场景
    current_scenario = ""
    default_tier = "Mid"
    for name, info in SCENARIOS.items():
        if info["min"] <= user_budget <= info["max"]:
            current_scenario = name
            default_tier = info["tier"]
            break
    
    st.sidebar.subheader("当前匹配场景")
    st.sidebar.info(f"**{current_scenario}**\n\n推荐初始等级: {default_tier}")

    # 允许用户在推荐基础上微调 Tier
    if 'manual_tier' not in st.session_state:
        st.session_state.manual_tier = default_tier

    selected_tier = st.sidebar.selectbox("性能等级微调", TIERS_ORDER, 
                                        index=TIERS_ORDER.index(st.session_state.manual_tier))

    # --- 2. 核心组件筛选 (低价优先) ---
    # CPU 筛选
    all_cpus = []
    for brand in all_data.get('cpus', {}):
        all_cpus.extend([item for item in all_data['cpus'][brand] 
                         if item.get('tier', '').lower() == selected_tier.lower()])
    all_cpus = sorted(all_cpus, key=lambda x: get_val(x, 'price'))
    
    if not all_cpus:
        st.error("该等级暂无 CPU 数据")
        return

    selected_cpu = st.selectbox("确认 CPU 型号", all_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')

    # --- 3. 显卡过滤 (严格对等 + 0.8-3倍价格) ---
    available_gpus = sorted([
        g for g in all_data.get('gpus', {}).get('gpus', [])
        if g.get('tier', '').lower() == selected_tier.lower() 
        and cpu_p * 0.8 <= get_val(g, 'price') <= cpu_p * 3
    ], key=lambda x: get_val(x, 'price'))

    # --- 4. 其他配件 (相邻 Tier) ---
    idx = TIERS_ORDER.index(selected_tier)
    neighbor_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    
    # 主板
    socket = selected_cpu.get('socket')
    mb_series = [s['series'] for s in all_data.get('mb_series', {}).get('Motherboard_Series', []) if s['socket'] == socket]
    available_mbs = sorted([m for m in all_data.get('mb_models', {}).get('motherboard_models', []) 
                           if m['series'] in mb_series and m.get('tier', '').lower() in neighbor_tiers], 
                           key=lambda x: get_val(x, 'price'))

    # 内存/硬盘
    available_mem = sorted([m for m in all_data.get('memory', {}).get('memory_modules', []) 
                           if m.get('tier', '').lower() in neighbor_tiers], key=lambda x: get_val(x, 'price'))
    available_ssd = sorted([s for s in all_data.get('storage', {}).get('storage_devices', []) 
                           if s.get('tier', '').lower() in neighbor_tiers], key=lambda x: get_val(x, 'price'))

    # --- 5. 展示与动态建议 ---
    if available_gpus and available_mbs:
        col1, col2 = st.columns([2, 1])
        with col1:
            gpu = st.selectbox("选择显卡 (严格平衡)", available_gpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
            mb = st.selectbox("选择主板", available_mbs, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
            
            num_mem = 2 if selected_tier in ["High-Mid", "Flagship"] else 1
            mem = st.selectbox(f"选择内存 (x{num_mem})", available_mem, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
            ssd = st.selectbox("选择硬盘", available_ssd, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")

        with col2:
            total = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + (get_val(mem, 'price') * num_mem) + get_val(ssd, 'price')
            surplus = user_budget - total
            
            st.metric("方案总价", f"￥{total:.2f}")
            st.metric("剩余预算", f"￥{surplus:.2f}")

            st.write("### 💡 深度优化建议")
            if surplus > 1500:
                st.success("✨ 预算剩余充足，你可以：")
                st.write(f"1. **提升核心**：将性能等级调至 **{TIERS_ORDER[min(idx+1, 4)]}**")
                st.write(f"2. **图形增强**：手动更换该列表中更贵的显卡型号")
                st.write(f"3. **静音耐用**：增加预算投入到高品质电源与散热器")
            elif 500 <= surplus <= 1500:
                st.info("🎯 预算略有盈余：")
                st.write("- 建议增加内存容量或选择更大空间的 SSD")
                st.write("- 或者选择做工更好的主板型号")
            elif surplus < 0:
                st.error("⚠️ 预算超支：")
                st.write("- 建议降低一个性能等级或选择更入门的品牌")

            st.write("---")
            st.caption(f"当前配置适用于: {current_scenario}")
    else:
        st.warning("根据当前预算与等级，未找到完美平衡的配件。请尝试调整预算或手动切换等级。")

if __name__ == "__main__":
    main()
