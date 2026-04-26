import streamlit as st
import json
import os

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

# 定义场景与 Tier、预算的关联
SCENARIOS = {
    "办公/家用 (Low/Entry)": {"min": 2000, "max": 4000, "tier": "Entry", "rec_ram": 16, "rec_ssd": 512},
    "主流网游 (Entry/Mid)": {"min": 4001, "max": 7000, "tier": "Mid", "rec_ram": 16, "rec_ssd": 1024},
    "3A游戏/2K竞技 (Mid/High-Mid)": {"min": 7001, "max": 12000, "tier": "High-Mid", "rec_ram": 32, "rec_ssd": 1024},
    "4K创作/深度学习 (High-Mid/Flagship)": {"min": 12001, "max": 25000, "tier": "Flagship", "rec_ram": 64, "rec_ssd": 2048},
    "顶级发烧/生产力 (Flagship+)": {"min": 25001, "max": 999999, "tier": "Flagship", "rec_ram": 128, "rec_ssd": 4096}
}
TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

# 旗舰级准入线 (用于放开上限后的基础过滤)
TIER_CRITERIA = {
    "Flagship": {"min_gpu_price": 8000, "min_mb_price": 2000}
}

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
    if not item: return default
    val = item.get(key, default)
    try: return float(val) if key == 'price' else val
    except: return 0

# --- 主程序 ---
def main():
    st.title("🖥️ DIY PC 场景化平衡配置专家")
    all_data = load_data()

    # --- 1. 预算与场景锁定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=1000000, value=6500, step=500)
    
    current_scenario = ""
    default_tier = "Mid"
    for name, info in SCENARIOS.items():
        if info["min"] <= user_budget <= info["max"]:
            current_scenario = name
            default_tier = info["tier"]
            break
    
    st.sidebar.subheader("当前匹配场景")
    st.sidebar.info(f"**{current_scenario}**\n\n推荐初始等级: {default_tier}")

    if 'manual_tier' not in st.session_state:
        st.session_state.manual_tier = default_tier

    selected_tier = st.sidebar.selectbox("性能等级微调", TIERS_ORDER, 
                                        index=TIERS_ORDER.index(st.session_state.manual_tier))

    # --- 2. CPU 筛选 ---
    all_cpus = []
    cpu_data = all_data.get('cpus', {})
    for brand in cpu_data:
        all_cpus.extend([item for item in cpu_data[brand] 
                         if item.get('tier', '').lower() == selected_tier.lower()])
    
    # 兜底：如果该等级没CPU，抓全库最贵的
    if not all_cpus:
        for brand in cpu_data: all_cpus.extend(cpu_data[brand])
        all_cpus = sorted(all_cpus, key=lambda x: get_val(x, 'price'), reverse=True)[:5]

    selected_cpu = st.selectbox("确认 CPU 型号", all_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')

    # --- 3. 显卡与主板筛选逻辑 (修复旗舰逻辑) ---
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    
    if selected_tier == "Flagship":
        min_gpu_p = TIER_CRITERIA["Flagship"]["min_gpu_price"] 
        available_gpus = [g for g in all_gpus if get_val(g, 'price') >= min_gpu_p]
    else:
        # 普通等级：CPU价格的 0.8 - 3.0 倍左右作为平衡区间
        available_gpus = [g for g in all_gpus if cpu_p * 0.8 <= get_val(g, 'price') <= cpu_p * 3.5]
    
    # 显卡排序与兜底
    available_gpus = sorted(available_gpus, key=lambda x: get_val(x, 'price'), reverse=True)
    if not available_gpus: available_gpus = sorted(all_gpus, key=lambda x: get_val(x, 'price'), reverse=True)[:5]

    # 主板逻辑
    socket = selected_cpu.get('socket')
    mb_series_data = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    matching_series_names = [s['series'] for s in mb_series_data if s['socket'] == socket]
    
    idx = TIERS_ORDER.index(selected_tier)
    neighbor_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    
    available_mbs = [
        m for m in all_data.get('mb_models', {}).get('motherboard_models', [])
        if m['series'] in matching_series_names and 
        (selected_tier == "Flagship" or m.get('tier', '').lower() in neighbor_tiers)
    ]
    if selected_tier == "Flagship":
        available_mbs = [m for m in available_mbs if get_val(m, 'price') >= TIER_CRITERIA["Flagship"]["min_mb_price"]]
    
    available_mbs = sorted(available_mbs, key=lambda x: get_val(x, 'price'), reverse=True)
    if not available_mbs: available_mbs = [m for m in all_data.get('mb_models', {}).get('motherboard_models', []) if m['series'] in matching_series_names][:5]

    # --- 4. 存储筛选 ---
    available_mem = sorted([m for m in all_data.get('memory', {}).get('memory_modules', []) 
                           if m.get('tier', '').lower() in neighbor_tiers or selected_tier == "Flagship"], key=lambda x: get_val(x, 'price'))
    available_ssd = sorted([s for s in all_data.get('storage', {}).get('storage_devices', []) 
                           if s.get('tier', '').lower() in neighbor_tiers or selected_tier == "Flagship"], key=lambda x: get_val(x, 'price'))

    # --- 5. 展示与动态建议 ---
    if available_gpus and available_mbs:
        col1, col2 = st.columns([2, 1])
        with col1:
            gpu = st.selectbox("选择显卡 (严格平衡)", available_gpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
            mb = st.selectbox("选择主板", available_mbs, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
            
            st.markdown("---")
            st.subheader("存储扩展")
            
            rec_ram_size = SCENARIOS[current_scenario].get("rec_ram", 16)
            default_mem_count = 2 if (selected_tier in ["High-Mid", "Flagship"] or rec_ram_size >= 32) else 1
            
            st.caption(f"💡 内存建议: {rec_ram_size}GB (当前推荐 {default_mem_count} 条)")
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                mem = st.selectbox("选择内存型号", available_mem, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
            with col_m2:
                mem_count = st.number_input("内存数量", min_value=1, max_value=8, value=default_mem_count, key="mem_cnt")

            rec_ssd_size = SCENARIOS[current_scenario].get("rec_ssd", 1024)
            st.caption(f"💡 硬盘建议: {rec_ssd_size}GB ({rec_ssd_size/1024:.1f}TB) 或更高")
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                ssd = st.selectbox("选择硬盘型号", available_ssd, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
            with col_s2:
                ssd_count = st.number_input("硬盘数量", min_value=1, max_value=4, value=1, key="ssd_cnt")

        with col2:
            mem_total_p = get_val(mem, 'price') * mem_count
            ssd_total_p = get_val(ssd, 'price') * ssd_count
            total = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + mem_total_p + ssd_total_p
            surplus = user_budget - total
            
            st.metric("方案总价", f"￥{total:.2f}")
            st.metric("预算剩余", f"￥{surplus:.2f}", delta=f"{surplus:.2f}")
            
            if user_budget > 50000:
                st.write("### 👑 顶级发烧友定制建议")
            else:
                st.write("### 💡 深度优化建议")

            if surplus > 1500:
                st.success("✨ 预算充足，建议：")
                if user_budget > 50000:
                    st.write("1. **追求极致**：确保显卡为 RTX 4090，CPU 为 i9/R9")
                    st.write("2. **满血存储**：内存插满 4 条，SSD 选择 PCIe 5.0 型号")
                else:
                    st.write(f"1. **提升等级**：尝试调至 **{TIERS_ORDER[min(idx+1, 4)]}**")
                st.write("3. **外设/散热**：投入更多预算在 4K 144Hz 显示器或分体水冷")
            elif 0 <= surplus <= 1500:
                st.info("🎯 预算利用率极高，配置非常平衡！")
            else:
                st.error("⚠️ 预算超支：建议降低性能等级或减少存储数量。")

            st.write("---")
            st.caption(f"当前方案基于: {current_scenario}")
    else:
        st.warning("未能匹配到合适的配件，请尝试调整预算。")

if __name__ == "__main__":
    main()
