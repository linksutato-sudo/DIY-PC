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
    if selected_tier == "Flagship":
        # 旗舰等级：只要价格高于基准线就行，有多少钱花多少钱
        min_gpu_p = TIER_CRITERIA["Flagship"]["min_gpu_price"] 
        available_gpus = [g for g in all_gpus if get_val(g, 'price') >= min_gpu_p]
        
        min_mb_p = TIER_CRITERIA["Flagship"]["min_mb_price"]
        available_mbs = [m for m in all_mbs if get_val(m, 'price') >= min_mb_p]
    else:
        # 其他等级保持原有的“严格区间筛选”
        available_gpus = [g for g in all_gpus if min_gpu_p <= get_val(g, 'price') <= max_gpu_p]
        available_mbs = [m for m in all_mbs if min_mb_p <= get_val(m, 'price') <= max_mb_p]
       

    # --- 4. 其他配件 (相邻 Tier) ---
    idx = TIERS_ORDER.index(selected_tier)
    neighbor_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    
    # 主板
    # --- 1. 获取 CPU 价格作为基准 ---
    cpu_p = get_val(selected_cpu, 'price')

    # --- 2. 筛选主板 (Socket 匹配 + 相邻 Tier 匹配 + 价格比例过滤) ---
    socket = selected_cpu.get('socket')
    mb_series_data = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    matching_series_names = [s['series'] for s in mb_series_data if s['socket'] == socket]
    
    available_mbs = [
        m for m in all_data.get('mb_models', {}).get('motherboard_models', [])
        if (
            m['series'] in matching_series_names and           # 物理接口匹配
            m.get('tier', '').lower() in neighbor_tiers and    # 性能档次匹配
            cpu_p * 0.5 <= get_val(m, 'price') <= cpu_p * 1.5  # 价格配比逻辑 (0.5x - 1.5x)
        )
    ]
    
    # 3. 排序：低价优先
    available_mbs = sorted(available_mbs, key=lambda x: get_val(x, 'price'))

    # 内存/硬盘
    available_mem = sorted([m for m in all_data.get('memory', {}).get('memory_modules', []) 
                           if m.get('tier', '').lower() in neighbor_tiers], key=lambda x: get_val(x, 'price'))
    available_ssd = sorted([s for s in all_data.get('storage', {}).get('storage_devices', []) 
                           if s.get('tier', '').lower() in neighbor_tiers], key=lambda x: get_val(x, 'price'))

# --- 5. 展示与动态建议 ---
    if available_gpus and available_mbs:
        col1, col2 = st.columns([2, 1])
        with col1:
            # --- 核心组件选择 ---
            gpu = st.selectbox("选择显卡 (严格平衡)", available_gpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
            mb = st.selectbox("选择主板", available_mbs, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
            
            st.markdown("---")
            st.subheader("存储扩展")
            
            # --- 内存配置逻辑 ---
            # 动态建议逻辑：高端/旗舰默认双通道
            rec_ram_size = SCENARIOS[current_scenario].get("rec_ram", 16)
            default_mem_count = 2 if (selected_tier in ["High-Mid", "Flagship"] or rec_ram_size >= 32) else 1
            
            st.caption(f"💡 内存建议: {rec_ram_size}GB (当前推荐 {default_mem_count} 条)")
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                mem = st.selectbox("选择内存型号", available_mem, 
                                 format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
            with col_m2:
                mem_count = st.number_input("内存数量", min_value=1, max_value=8, value=default_mem_count, key="mem_cnt")

            # --- 硬盘配置逻辑 ---
            rec_ssd_size = SCENARIOS[current_scenario].get("rec_ssd", 1024)
            st.caption(f"💡 硬盘建议: {rec_ssd_size}GB ({rec_ssd_size/1024:.1f}TB) 或更高")
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                ssd = st.selectbox("选择硬盘型号", available_ssd, 
                                 format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
            with col_s2:
                ssd_count = st.number_input("硬盘数量", min_value=1, max_value=4, value=1, key="ssd_cnt")

        with col2:
            # --- 价格实时计算 ---
            mem_total_p = get_val(mem, 'price') * mem_count
            ssd_total_p = get_val(ssd, 'price') * ssd_count
            gpu_p = get_val(gpu, 'price')
            mb_p = get_val(mb, 'price')
            
            total = cpu_p + gpu_p + mb_p + mem_total_p + ssd_total_p
            surplus = user_budget - total
            
            # --- 状态看板 ---
            st.metric("方案总价", f"￥{total:.2f}")
            # 根据剩余预算显示颜色 (delta 为正绿色，负红色)
            st.metric("预算剩余", f"￥{surplus:.2f}", delta=f"{surplus:.2f}")
            
            st.write("### 💡 深度优化建议")
            if surplus > 1500:
                st.success("✨ 预算充足，性能还可以再顶一顶！")
                st.write(f"1. **提升等级**：尝试调至 **{TIERS_ORDER[min(idx+1, len(TIERS_ORDER)-1)]}**")
                st.write("2. **核心增强**：手动在左侧列表选购更高频的 CPU/GPU")
                st.write("3. **颜值/静音**：多余预算可投入高端机箱和水冷")
            elif 0 <= surplus <= 1500:
                st.info("🎯 预算利用率极高！")
                if surplus > 500:
                    st.write("- 建议多买一条内存或升级 2TB SSD")
                    st.write("- 或者换一个售后更稳的金牌电源")
                else:
                    st.write("- 目前配置非常平衡，适合直接下手")
            else:
                st.error("⚠️ 预算超支了！")
                st.write("- 建议降低一级性能等级")
                st.write("- 或者适当减少内存/硬盘数量/容量")

            st.write("---")
            st.caption(f"当前方案基于: {current_scenario}")
    else:
        st.warning("根据当前预算与等级，未找到完美平衡的配件。请尝试调整预算或手动切换等级。")

if __name__ == "__main__":
    main()
