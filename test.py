import streamlit as st
import json
import os
import math

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

# 定义场景与配置标准
SCENARIOS = {
    "办公/家用 (Low/Entry)": {"min": 2000, "max": 4000, "tier": "Entry", "rec_ram": 16, "rec_ssd": 512},
    "主流网游 (Entry/Mid)": {"min": 4001, "max": 7000, "tier": "Mid", "rec_ram": 16, "rec_ssd": 1024},
    "3A游戏/2K竞技 (Mid/High-Mid)": {"min": 7001, "max": 12000, "tier": "High-Mid", "rec_ram": 32, "rec_ssd": 1024},
    "4K创作/深度学习 (High-Mid/Flagship)": {"min": 12001, "max": 25000, "tier": "Flagship", "rec_ram": 64, "rec_ssd": 2048},
    "顶级发烧/生产力 (Flagship+)": {"min": 25001, "max": 999999, "tier": "Flagship", "rec_ram": 128, "rec_ssd": 4096}
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
    if not item: return default
    val = item.get(key, default)
    try: return float(val) if key == 'price' else val
    except: return 0

def main():
    st.title("🖥️ DIY PC 场景化平衡配置专家")
    all_data = load_data()

    # --- 1. 预算与场景判定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=1000000, value=6500, step=500)
    
    # 确定场景
    current_scenario = next((name for name, info in SCENARIOS.items() if info["min"] <= user_budget <= info["max"]), "办公/家用 (Low/Entry)")
    scenario_info = SCENARIOS[current_scenario]
    
    st.sidebar.subheader("当前匹配场景")
    st.sidebar.info(f"**{current_scenario}**")

    # 性能等级控制
    if 'prev_scenario' not in st.session_state or st.session_state.prev_scenario != current_scenario:
        st.session_state.manual_tier = scenario_info["tier"]
        st.session_state.prev_scenario = current_scenario

    selected_tier = st.sidebar.selectbox("性能等级微调", TIERS_ORDER, index=TIERS_ORDER.index(st.session_state.manual_tier))

    # --- 2. 核心组件匹配核心逻辑 ---
    # CPU 筛选
    cpu_data = all_data.get('cpus', {})
    available_cpus = []
    for brand in cpu_data:
        available_cpus.extend([item for item in cpu_data[brand] if item.get('tier', '').lower() == selected_tier.lower()])
    
    if not available_cpus: # 降级兜底
        for brand in cpu_data: available_cpus.extend(cpu_data[brand])
        available_cpus = sorted(available_cpus, key=lambda x: get_val(x, 'price'), reverse=True)[:10]

    selected_cpu = st.selectbox("确认 CPU 型号", available_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')

    # --- 3. 显卡与主板价格匹配算法 ---
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    all_mbs = all_data.get('mb_models', {}).get('motherboard_models', [])
    
    # 根据等级设定价格权重的搜索区间
    # 旗舰不再设上限，低端注重性价比
    if selected_tier == "Flagship":
        gpu_min, gpu_max = cpu_p * 1.5, 999999
        mb_min, mb_max = cpu_p * 0.7, 999999
    elif selected_tier == "High-Mid":
        gpu_min, gpu_max = cpu_p * 1.2, cpu_p * 3.5
        mb_min, mb_max = cpu_p * 0.5, cpu_p * 1.2
    else:
        gpu_min, gpu_max = cpu_p * 0.6, cpu_p * 2.0
        mb_min, mb_max = cpu_p * 0.4, cpu_p * 1.0

    # 筛选显卡
    filtered_gpus = [g for g in all_gpus if gpu_min <= get_val(g, 'price') <= gpu_max]
    if not filtered_gpus: # 匹配失效兜底：抓取全库价格最接近该区间的显卡
        filtered_gpus = sorted(all_gpus, key=lambda x: abs(get_val(x, 'price') - (gpu_min + gpu_max)/2))[:10]
    
    # 筛选主板 (Socket必须匹配)
    socket = selected_cpu.get('socket')
    matching_series = [s['series'] for s in all_data.get('mb_series', {}).get('Motherboard_Series', []) if s['socket'] == socket]
    filtered_mbs = [m for m in all_mbs if m['series'] in matching_series and mb_min <= get_val(m, 'price') <= mb_max]
    if not filtered_mbs: # 匹配失效兜底
        filtered_mbs = [m for m in all_mbs if m['series'] in matching_series]
        filtered_mbs = sorted(filtered_mbs, key=lambda x: abs(get_val(x, 'price') - (mb_min + mb_max)/2))[:10]

    # --- 4. 存储逻辑：自动计算推荐数量 ---
    # 获取存储设备库
    raw_mem = all_data.get('memory', {}).get('memory_modules', [])
    raw_ssd = all_data.get('storage', {}).get('storage_devices', [])
    
    # 针对 Flagship 放开 Tier 限制，其他等级允许相邻 Tier
    idx = TIERS_ORDER.index(selected_tier)
    allowed_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    if selected_tier == "Flagship": allowed_tiers.append("high-mid")

    available_mem = [m for m in raw_mem if m.get('tier', '').lower() in allowed_tiers]
    available_ssd = [s for s in raw_ssd if s.get('tier', '').lower() in allowed_tiers]

    # --- 5. 渲染展示区 ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        gpu = st.selectbox("选择显卡", sorted(filtered_gpus, key=lambda x: get_val(x, 'price')), format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
        mb = st.selectbox("选择主板", sorted(filtered_mbs, key=lambda x: get_val(x, 'price')), format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
        
        st.markdown("---")
        st.subheader("存储扩展 (已根据场景自动推荐数量)")
        
        # 内存数量自动推荐逻辑
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            mem = st.selectbox("选择内存型号", available_mem, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
        with col_m2:
            # 自动计算：推荐容量 / 单条容量 = 数量
            single_mem_capacity = int(mem['display_name'].split('GB')[0].split(' ')[-1]) if 'GB' in mem['display_name'] else 8
            auto_mem_count = max(1, math.ceil(scenario_info["rec_ram"] / single_mem_capacity))
            # 修正：通常内存为2/4条
            if auto_mem_count == 3: auto_mem_count = 4 
            mem_count = st.number_input("数量", min_value=1, max_value=8, value=int(auto_mem_count), key="mem_cnt_auto")

        # 硬盘数量自动推荐逻辑
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            ssd = st.selectbox("选择硬盘型号", available_ssd, format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
        with col_s2:
            # 自动计算：推荐容量 / 单个硬盘容量 = 数量
            single_ssd_capacity = 1024 # 默认1T
            if '1TB' in ssd['display_name']: single_ssd_capacity = 1024
            elif '2TB' in ssd['display_name']: single_ssd_capacity = 2048
            elif '512GB' in ssd['display_name']: single_ssd_capacity = 512
            
            auto_ssd_count = max(1, math.ceil(scenario_info["rec_ssd"] / single_ssd_capacity))
            ssd_count = st.number_input("数量", min_value=1, max_value=4, value=int(auto_ssd_count), key="ssd_cnt_auto")

    with col2:
        # --- 价格看板 ---
        total = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + (get_val(mem, 'price') * mem_count) + (get_val(ssd, 'price') * ssd_count)
        surplus = user_budget - total
        
        st.metric("方案总价", f"￥{total:.2f}")
        st.metric("预算剩余", f"￥{surplus:.2f}", delta=f"{surplus:.2f}")

        st.write("### ⚖️ 配置平衡性报告")
        # 简单算法：判断显卡是否比CPU贵太多或便宜太多
        gpu_ratio = get_val(gpu, 'price') / cpu_p if cpu_p > 0 else 1
        if gpu_ratio > 4: st.warning("⚠️ 显卡过强，CPU可能存在性能瓶颈。")
        elif gpu_ratio < 0.5: st.warning("⚠️ CPU过强，显卡可能无法完全发挥。")
        else: st.success("✅ 核心组件配比科学。")
        
        if (mem_count * single_mem_capacity) < scenario_info["rec_ram"]:
            st.error(f"❌ 内存低于场景推荐 ({scenario_info['rec_ram']}GB)")
        
        st.write("---")
        st.caption(f"当前配置适用于: {current_scenario}")

if __name__ == "__main__":
    main()
