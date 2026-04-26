import streamlit as st
import json
import os
import math

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

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
    try: return float(val) if key in ['price', 'pcie', 'capacity'] else val
    except: return 0

def main():
    st.title("🖥️ DIY PC 场景化平衡配置专家")
    all_data = load_data()

    # --- 1. 侧边栏：预算与场景判定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=1000000, value=6500, step=500)
    
    default_scenario = next((name for name, info in SCENARIOS.items() if info["min"] <= user_budget <= info["max"]), "办公/家用 (Low/Entry)")
    current_scenario = st.sidebar.selectbox("当前匹配场景", list(SCENARIOS.keys()), index=list(SCENARIOS.keys()).index(default_scenario))
    
    base_tier = SCENARIOS[current_scenario]["tier"]
    try:
        base_idx = TIERS_ORDER.index(base_tier)
    except ValueError:
        base_idx = 0

    if base_tier == "Flagship":
        allowed_tiers = ["Flagship"]
    else:
        allowed_tiers = TIERS_ORDER[base_idx : min(base_idx + 2, len(TIERS_ORDER))]

    if 'prev_scenario' not in st.session_state or st.session_state.prev_scenario != current_scenario:
        st.session_state.manual_tier = base_tier
        st.session_state.prev_scenario = current_scenario

    if st.session_state.manual_tier not in allowed_tiers:
        st.session_state.manual_tier = base_tier

    selected_tier = st.sidebar.selectbox("性能等级微调", allowed_tiers, index=allowed_tiers.index(st.session_state.manual_tier))

    scenario_info = SCENARIOS[current_scenario].copy()
    if selected_tier == "Flagship":
        scenario_info["rec_ram"] = max(scenario_info["rec_ram"], 64)
        scenario_info["rec_ssd"] = max(scenario_info["rec_ssd"], 2048)
    elif selected_tier == "High":
        scenario_info["rec_ram"] = max(scenario_info["rec_ram"], 32)

    st.sidebar.info(f"💡 场景需求：{scenario_info['rec_ram']}GB 内存 | {scenario_info['rec_ssd']}GB 存储")

    # --- 2. CPU 筛选 ---
    cpu_data = all_data.get('cpus', {})
    available_cpus = []
    for brand in cpu_data:
        available_cpus.extend([item for item in cpu_data[brand] if item.get('tier', '').lower() == selected_tier.lower()])
    
    if not available_cpus: 
        for brand in cpu_data: available_cpus.extend(cpu_data[brand])
        available_cpus = sorted(available_cpus, key=lambda x: get_val(x, 'price'), reverse=True)[:10]

    selected_cpu = st.selectbox("确认 CPU 型号", available_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')

    # --- 3. 显卡与主板筛选 (增加主板规格提取) ---
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    all_mb_models = all_data.get('mb_models', {}).get('motherboard_models', [])
    all_mb_series = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    
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
    # 建立系列查询字典：{ "H81": {"ddr": "DDR3", "pcie": "3.0"}, ... }
    series_map = {s['series']: s for s in all_mb_series if s['socket'] == socket}
    matching_series_names = list(series_map.keys())
    
    filtered_mbs = [m for m in all_mb_models if m['series'] in matching_series_names and mb_min <= get_val(m, 'price') <= mb_max]
    if not filtered_mbs:
        filtered_mbs = [m for m in all_mb_models if m['series'] in matching_series_names]
        filtered_mbs = sorted(filtered_mbs, key=lambda x: abs(get_val(x, 'price') - (mb_min + mb_max)/2))[:10]
    
# --- 4. 存储逻辑筛选 (最终修复版：统一大小写 + 逻辑去重) ---
        raw_mem = all_data.get('memory', {}).get('memory_modules', [])
        raw_ssd = all_data.get('storage', {}).get('storage_devices', [])
        
        # 强制统一主板规格为大写字符串/浮点数
        current_mb_spec = series_map.get(mb['series'], {})
        
        # 获取主板 DDR 类型并转大写，例如 "DDR4"
        mb_ddr_target = str(current_mb_spec.get('ddr', 'DDR4')).strip().upper()
        # 获取主板 PCIe 版本
        mb_pcie_limit = get_val(current_mb_spec, 'pcie', 3.0)

        # 1. 物理规格初筛 (确保插槽兼容)
        # 内存：匹配 type (转大写比较)
        phy_mem = [
            m for m in raw_mem 
            if str(m.get('type', '')).strip().upper() == mb_ddr_target
        ]
        
        # 硬盘：匹配 PCIe 版本
        phy_ssd = [
            s for s in raw_ssd 
            if get_val(s, 'pcie') <= mb_pcie_limit
        ]

        # 2. 档次筛选 (在物理兼容基础上尝试 Tier 匹配)
        idx = TIERS_ORDER.index(selected_tier)
        # 计算允许的 Tier 范围
        allowed_storage_tiers = [
            t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]
        ]
        
        available_mem = [
            m for m in phy_mem 
            if str(m.get('tier', '')).lower() in allowed_storage_tiers
        ]
        available_ssd = [
            s for s in phy_ssd 
            if str(s.get('tier', '')).lower() in allowed_storage_tiers
        ]


    # --- 5. 渲染展示区 (先选主板，确定规格后再选存储) ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        gpu = st.selectbox("选择显卡", sorted(filtered_gpus, key=lambda x: get_val(x, 'price')), 
                           format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
        
        mb = st.selectbox("选择主板", sorted(filtered_mbs, key=lambda x: get_val(x, 'price')), 
                          format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
        
        # --- 获取主板物理属性用于后续匹配 ---
        current_mb_series_info = series_map.get(mb['series'], {})
        mb_ddr_type = current_mb_series_info.get('ddr', 'DDR4').upper()
        mb_pcie_ver = get_val(current_mb_series_info, 'pcie', 3.0)

        mb_tags = mb.get('tags', [])
        if mb_tags:
            tag_items = "".join([f'<span style="background-color: #f0f2f6; color: #31333f; padding: 2px 10px; border-radius: 12px; margin: 0 6px 6px 0; font-size: 0.85rem; border: 1px solid #d1d5db; display: inline-block;">{tag}</span>' for tag in mb_tags])
            st.markdown(f'<div style="display: flex; flex-wrap: wrap; align-items: center; line-height: 1.6; margin-top: 5px;"><span style="margin-right: 8px;">🏷️ 主板特性:</span>{tag_items}</div>', unsafe_allow_html=True)
        else:
            st.caption("ℹ️ 该主板暂无详细特性说明")
            
        st.markdown("---")
        st.subheader("存储扩展 (规格已自动匹配主板)")


        # 3. 保底机制：如果当前档次没条子，就给用户看所有能插上去的
        if not available_mem:
            available_mem = phy_mem
            if phy_mem:
                st.info(f"💡 当前档次无匹配，已显示所有兼容的 {mb_ddr_target} 内存")
        
        if not available_ssd:
            available_ssd = phy_ssd
            if phy_ssd:
                st.info(f"💡 当前档次无匹配，已显示所有 PCIe {mb_pcie_limit} 及以下的硬盘")
        if not available_mem: st.warning(f"⚠️ 未找到匹配的 {mb_ddr_type} 内存")
        if not available_ssd: st.warning(f"⚠️ 未找到匹配的 PCIe {mb_pcie_ver} 硬盘")

        # --- 内存数量自动推荐 ---
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            mem = st.selectbox("选择内存型号", available_mem, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}",
                               key=f"mem_select_{mb['model']}")
        with col_m2:
            single_mem_cap = get_val(mem, 'capacity', 8) 
            auto_mem_count = max(1, math.ceil(scenario_info["rec_ram"] / (single_mem_cap if single_mem_cap > 0 else 8)))
            if get_val(mem, 'sticks', 1) >= 2: auto_mem_count = 1
            mem_count = st.number_input("数量", 1, 8, value=min(int(auto_mem_count), 8), key=f"mem_cnt_{mb['model']}")
    
        # --- 硬盘数量自动推荐 ---
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            ssd = st.selectbox("选择硬盘型号", available_ssd, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}",
                               key=f"ssd_select_{mb['model']}")
        with col_s2:
            single_ssd_cap = get_val(ssd, 'capacity', 1024)
            auto_ssd_count = max(1, math.ceil((scenario_info["rec_ssd"] * 0.95) / (single_ssd_cap if single_ssd_cap > 0 else 1024)))
            ssd_count = st.number_input("数量", 1, 4, value=min(int(auto_ssd_count), 4), key=f"ssd_cnt_{mb['model']}")
    
    with col2:
        actual_mem_total = get_val(mem, 'capacity', 0) * mem_count
        actual_ssd_total = get_val(ssd, 'capacity', 0) * ssd_count
        
        total = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + \
                (get_val(mem, 'price') * mem_count) + (get_val(ssd, 'price') * ssd_count)
        surplus = user_budget - total
        
        st.metric("方案总价", f"￥{total:.2f}")
        st.metric("预算剩余", f"￥{surplus:.2f}", delta=f"{surplus:.2f}")
    
        st.write("### ⚖️ 配置平衡性报告")
        
        # 兼容性汇总显示
        st.info(f"📋 物理规格确认:\n- 主板插槽: {socket}\n- 内存需求: {mb_ddr_type}\n- 最大硬盘: PCIe {mb_pcie_ver}")

        gpu_ratio = get_val(gpu, 'price') / cpu_p if cpu_p > 0 else 1
        if gpu_ratio > 4: st.warning("⚠️ 显卡过强，CPU可能存在性能瓶颈。")
        elif gpu_ratio < 0.5: st.warning("⚠️ CPU过强，显卡可能无法完全发挥。")
        else: st.success("✅ 核心组件配比科学。")
        
        if actual_mem_total < scenario_info["rec_ram"]:
            st.error(f"❌ 内存不足: 当前 {actual_mem_total}GB < 推荐 {scenario_info['rec_ram']}GB")
        else:
            st.success(f"✅ 内存充足: 已达 {actual_mem_total}GB")
    
        if actual_ssd_total < (scenario_info["rec_ssd"] * 0.95):
            st.info(f"📂 存储较小: 当前 {actual_ssd_total}GB < 建议 {scenario_info['rec_ssd']}GB")
        else:
            st.success(f"✅ 存储充足: 已达 {actual_ssd_total}GB")
        
        st.write("---")
        st.caption(f"当前配置适用于: {current_scenario} ({selected_tier} 模式)")

if __name__ == "__main__":
    main()
