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

    # --- 1. 侧边栏：预算与场景判定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=1000000, value=6500, step=500)
    
    # 自动匹配场景
    default_scenario = next((name for name, info in SCENARIOS.items() if info["min"] <= user_budget <= info["max"]), "办公/家用 (Low/Entry)")
    current_scenario = st.sidebar.selectbox("当前匹配场景", list(SCENARIOS.keys()), index=list(SCENARIOS.keys()).index(default_scenario))
    
    # --- 新增：智能性能等级过滤逻辑 ---
    # 定义不同场景允许出现的性能等级
    # 比如：顶级发烧场景不允许选 Low，入门场景不允许选 Flagship
    scenario_to_tiers = {
        "顶级发烧/生产力 (Flagship+)": ["Medium", "High", "Flagship"],
        "深度游戏/设计": ["Low", "Medium", "High", "Flagship"],
        "主流游戏/办公": ["Low", "Medium", "High"],
        "办公/家用 (Low/Entry)": ["Low", "Medium"]
    }
    
    # 获取当前场景可用的等级列表，如果没有定义则默认使用全部 TIERS_ORDER
    allowed_tiers = scenario_to_tiers.get(current_scenario, TIERS_ORDER)
    
    # 性能等级微调
    if 'prev_scenario' not in st.session_state or st.session_state.prev_scenario != current_scenario:
        # 如果场景变了，默认等级也要重置到场景对应的默认值，且必须在 allowed_tiers 内
        default_tier = SCENARIOS[current_scenario]["tier"]
        st.session_state.manual_tier = default_tier if default_tier in allowed_tiers else allowed_tiers[0]
        st.session_state.prev_scenario = current_scenario

    # 动态渲染性能等级下拉框
    selected_tier = st.sidebar.selectbox(
        "性能等级微调", 
        allowed_tiers, 
        index=allowed_tiers.index(st.session_state.manual_tier) if st.session_state.manual_tier in allowed_tiers else 0
    )

    # --- 动态计算推荐标准 ---
    scenario_info = SCENARIOS[current_scenario].copy()
    # 简单的性能微调逻辑
    if selected_tier == "Low":
        scenario_info["rec_ram"] = max(8, scenario_info["rec_ram"] // 2)
    elif selected_tier == "Flagship":
        scenario_info["rec_ram"] = max(scenario_info["rec_ram"], 64)

    st.sidebar.info(f"💡 场景需求：{scenario_info['rec_ram']}GB 内存 | {scenario_info['rec_ssd']}GB 存储")

    # --- 2. 核心组件匹配 ---
    cpu_data = all_data.get('cpus', {})
    available_cpus = []
    for brand in cpu_data:
        available_cpus.extend([item for item in cpu_data[brand] if item.get('tier', '').lower() == selected_tier.lower()])
    
    if not available_cpus: 
        for brand in cpu_data: available_cpus.extend(cpu_data[brand])
        available_cpus = sorted(available_cpus, key=lambda x: get_val(x, 'price'), reverse=True)[:10]

    selected_cpu = st.selectbox("确认 CPU 型号", available_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')

    # 显卡与主板筛选逻辑 (保持原样)
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    all_mbs = all_data.get('mb_models', {}).get('motherboard_models', [])
    
    if selected_tier == "Flagship":
        gpu_min, gpu_max = cpu_p * 1.5, 999999
        mb_min, mb_max = cpu_p * 0.7, 999999
    elif selected_tier == "High-Mid":
        gpu_min, gpu_max = cpu_p * 1.2, cpu_p * 3.5
        mb_min, mb_max = cpu_p * 0.5, cpu_p * 1.2
    else:
        gpu_min, gpu_max = cpu_p * 0.6, cpu_p * 2.0
        mb_min, mb_max = cpu_p * 0.4, cpu_p * 1.0

    filtered_gpus = [g for g in all_gpus if gpu_min <= get_val(g, 'price') <= gpu_max]
    if not filtered_gpus:
        filtered_gpus = sorted(all_gpus, key=lambda x: abs(get_val(x, 'price') - (gpu_min + gpu_max)/2))[:10]
    
    socket = selected_cpu.get('socket')
    matching_series = [s['series'] for s in all_data.get('mb_series', {}).get('Motherboard_Series', []) if s['socket'] == socket]
    filtered_mbs = [m for m in all_mbs if m['series'] in matching_series and mb_min <= get_val(m, 'price') <= mb_max]
    if not filtered_mbs:
        filtered_mbs = [m for m in all_mbs if m['series'] in matching_series]
        filtered_mbs = sorted(filtered_mbs, key=lambda x: abs(get_val(x, 'price') - (mb_min + mb_max)/2))[:10]

    # --- 4. 存储逻辑筛选 ---
    raw_mem = all_data.get('memory', {}).get('memory_modules', [])
    raw_ssd = all_data.get('storage', {}).get('storage_devices', [])
    
    idx = TIERS_ORDER.index(selected_tier)
    allowed_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    available_mem = [m for m in raw_mem if m.get('tier', '').lower() in allowed_tiers]
    available_ssd = [s for s in raw_ssd if s.get('tier', '').lower() in allowed_tiers]

# --- 5. 渲染展示区 ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 显卡和主板选择 (保持你原有的逻辑)
        gpu = st.selectbox("选择显卡", sorted(filtered_gpus, key=lambda x: get_val(x, 'price')), 
                           format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
        mb = st.selectbox("选择主板", sorted(filtered_mbs, key=lambda x: get_val(x, 'price')), 
                          format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
        
        # --- 主板型号说明 (Tags) - 这里的 HTML 逻辑保持不变 ---
        mb_tags = mb.get('tags', [])
        if mb_tags:
            tag_items = "".join([
                f'<span style="background-color: #f0f2f6; color: #31333f; padding: 2px 10px; '
                f'border-radius: 12px; margin: 0 6px 6px 0; font-size: 0.85rem; '
                f'border: 1px solid #d1d5db; display: inline-block;">{tag}</span>' 
                for tag in mb_tags
            ])
            tag_html = f'<div style="display: flex; flex-wrap: wrap; align-items: center; line-height: 1.6;"><span style="margin-right: 8px;">🏷️ 主板特性:</span>{tag_items}</div>'
            st.markdown(tag_html, unsafe_allow_html=True)
        else:
            st.caption("ℹ️ 该主板暂无详细特性说明")
        
        st.markdown("---")
        st.subheader("存储扩展 (已根据场景自动推荐数量)")

        # --- 内存数量自动推荐 ---
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            mem = st.selectbox("选择内存型号", available_mem, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
        with col_m2:
            single_mem_cap = get_val(mem, 'capacity', 8) 
            auto_mem_count = max(1, math.ceil(scenario_info["rec_ram"] / single_mem_cap))
            if get_val(mem, 'sticks', 1) >= 2: auto_mem_count = 1
            
            # --- 修复点：添加 min(value, max_value) 保护，并在 key 中加入 selected_tier ---
            safe_mem_val = min(int(auto_mem_count), 8)
            mem_count = st.number_input("数量", 1, 8, value=safe_mem_val, 
                                        key=f"mem_cnt_{current_scenario}_{selected_tier}")
    
        # --- 硬盘数量自动推荐 ---
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            ssd = st.selectbox("选择硬盘型号", available_ssd, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
        with col_s2:
            single_ssd_cap = get_val(ssd, 'capacity', 1024)
            auto_ssd_count = max(1, math.ceil((scenario_info["rec_ssd"] * 0.95) / single_ssd_cap))
            
            # --- 修复点：添加 min(value, max_value) 保护，并在 key 中加入 selected_tier ---
            safe_ssd_val = min(int(auto_ssd_count), 4)
            ssd_count = st.number_input("数量", 1, 4, value=safe_ssd_val, 
                                        key=f"ssd_cnt_{current_scenario}_{selected_tier}")

if __name__ == "__main__":
    main()
