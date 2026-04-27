import streamlit as st
import json
import os
import math

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

# 1. 核心场景逻辑配置 (整合了 prefer_single_mem 参数)
SCENARIOS = {
    "办公/家用 (Low/Entry)": {
        "min": 3000, "max": 5500, "tier": "Low", "rec_ram": 16, 
        "main_ssd_rec": "128GB - 256GB", "main_ssd_val": 120, 
        "sub_storage": "HDD", "sub_desc": "大容量机械硬盘 (存放资料)",
        "prefer_single_mem": 8  # 办公场景偏好单条8G
    },
    "主流网游 (Entry/Mid)": {
        "min": 5501, "max": 9000, "tier": "Mid", "rec_ram": 16, 
        "main_ssd_rec": "512GB", "main_ssd_val": 480, 
        "sub_storage": "SSD", "sub_desc": "高速固态硬盘 (快速加载游戏)",
        "prefer_single_mem": 16 # 网游偏好单条16G
    },
    "3A游戏/2K竞技 (Mid/High-Mid)": {
        "min": 9001, "max": 18000, "tier": "High-Mid", "rec_ram": 32, 
        "main_ssd_rec": "1TB", "main_ssd_val": 932, 
        "sub_storage": "SSD", "sub_desc": "高速固态硬盘 (减少场景卡顿)",
        "prefer_single_mem": 16
    },
    "4K创作/深度学习 (High-Mid/Flagship)": {
        "min": 18001, "max": 25000, "tier": "Flagship", "rec_ram": 64, 
        "main_ssd_rec": "2TB", "main_ssd_val": 1864, 
        "sub_storage": "SSD", "sub_desc": "高性能 NVMe (处理大型素材)",
        "prefer_single_mem": 32 # 生产力偏好单条32G
    },
    "顶级发烧/生产力 (Flagship+)": {
        "min": 25001, "max": 999999, "tier": "Flagship", "rec_ram": 128, 
        "main_ssd_rec": "4TB+", "main_ssd_val": 3728, 
        "sub_storage": "SSD", "sub_desc": "顶尖 NVMe 阵列",
        "prefer_single_mem": 32
    }
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
        except:
            data[key] = {}
    return data

def get_val(item, key, default=0):
    if not item: return default
    val = item.get(key, default)
    try:
        num_keys = ['price', 'pcie', 'capacity', 'm2_slots', 'max_storage_drives', 'ram_slots_count', 'ram_frequency']
        if key in num_keys:
            return float(val) if val is not None else default
        return val
    except:
        return default

def main():
    st.title("🖥️ DIY PC 场景化平衡配置推荐")
    all_data = load_data()

    # --- 1. 侧边栏：预算与场景判定 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, value=6500, step=500)
    
    default_scenario = next((name for name, info in SCENARIOS.items() if info["min"] <= user_budget <= info["max"]), "办公/家用 (Low/Entry)")
    current_scenario = st.sidebar.selectbox("当前匹配场景", list(SCENARIOS.keys()), index=list(SCENARIOS.keys()).index(default_scenario))
    
    scenario_info = SCENARIOS[current_scenario]
    base_tier = scenario_info["tier"]
    
    # 等级过滤逻辑
    try:
        base_idx = TIERS_ORDER.index(base_tier)
    except ValueError:
        base_idx = 0
    allowed_tiers = ["Flagship"] if base_tier == "Flagship" else TIERS_ORDER[base_idx : min(base_idx + 2, len(TIERS_ORDER))]
    selected_tier = st.sidebar.selectbox("性能等级微调", allowed_tiers)
    
    st.sidebar.markdown(f"""
    ---
    **📋 {current_scenario} 建议指标：**
    - 🧠 **内存**: {scenario_info['rec_ram']}GB
    - 💾 **主盘**: {scenario_info['main_ssd_rec']} SSD
    """)

    # --- 2. CPU 选择 ---
    cpu_data = all_data.get('cpus', {})
    available_cpus = []
    for brand in cpu_data:
        available_cpus.extend([item for item in cpu_data[brand] if item.get('tier', '').lower() == selected_tier.lower()])
    if not available_cpus:
        for brand in cpu_data: available_cpus.extend(cpu_data[brand])
        available_cpus = sorted(available_cpus, key=lambda x: get_val(x, 'price'))[:10]

    selected_cpu = st.selectbox("确认 CPU 型号", available_cpus, format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}")
    cpu_p = get_val(selected_cpu, 'price')
    cpu_socket = selected_cpu.get('socket', '未知接口')
    st.warning(f"💡 **注意：** 该 CPU 支持 **{selected_cpu.get('supported_motherboards', '对应接口')}** 系列型号的主板")

    # --- 3. 核心平衡筛选逻辑 (CPU/显卡/主板联动) ---
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    all_mb_models = all_data.get('mb_models', {}).get('motherboard_models', [])
    all_mb_series = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    
    # 价格区间倍数计算
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
    idx = TIERS_ORDER.index(selected_tier)
    allowed_gpu_tiers = [t.lower() for t in TIERS_ORDER[max(0, idx-1):min(len(TIERS_ORDER), idx+2)]]
    filtered_gpus = [g for g in all_gpus if (gpu_min <= get_val(g, 'price') <= gpu_max) and (g.get('tier', '').lower() in allowed_gpu_tiers)]
    if not filtered_gpus: filtered_gpus = sorted(all_gpus, key=lambda x: abs(get_val(x, 'price') - (gpu_min + gpu_max)/2))[:10]
    
    # 筛选主板
    series_map = {s['series']: s for s in all_mb_series if s['socket'] == cpu_socket}
    filtered_mbs = [m for m in all_mb_models if m['series'] in series_map and mb_min <= get_val(m, 'price') <= mb_max]
    if not filtered_mbs: filtered_mbs = [m for m in all_mb_models if m['series'] in series_map]

    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        gpu = st.selectbox("选择显卡", sorted(filtered_gpus, key=lambda x: get_val(x, 'price')), format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
        mb = st.selectbox("选择主板", sorted(filtered_mbs, key=lambda x: get_val(x, 'price')), format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
        
        # 提取主板物理规格
        mb_ram_type = mb.get('ram_type', 'DDR4')
        mb_ram_slots = int(get_val(mb, 'ram_slots_count', 2))
        mb_ram_freq = get_val(mb, 'ram_frequency', 3200)
        mb_m2_slots = int(get_val(mb, 'm2_slots', 1))
        mb_max_drives = int(get_val(mb, 'max_storage_drives', 4))

        st.info(f"🏗️ **主板物理上限：** 内存槽 x{mb_ram_slots} ({mb_ram_type} {int(mb_ram_freq)}MHz) | M.2槽 x{mb_m2_slots} | 总盘位 x{mb_max_drives}")
        
        #主板特性
        mb_tags = mb.get('tags', [])
        if mb_tags:
            # 构建 HTML 字符串
            # justify-content: flex-start 确保从左对齐，flex-wrap: wrap 负责自动换行
            tag_html = f"""
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 5px;">
                {" ".join([f'<span style="background-color: #f0f2f6; color: #31333F; padding: 2px 10px; border-radius: 15px; font-size: 0.85rem; border: 1px solid #dcdfe6; white-space: nowrap;">{t}</span>' for t in mb_tags])}
            </div>
            """
            st.write("🏷️ **主板特性：**")
            st.markdown(tag_html, unsafe_allow_html=True)


        # --- 4. 内存方案 (整合了 temp_test 的自动匹配和按钮逻辑) ---
        st.subheader("内存方案")
        raw_mem = all_data.get('memory', {}).get('memory_modules', [])
        # 过滤主板支持的类型 (DDR4/DDR5)
        phy_mem = [m for m in raw_mem if m.get('type', '').upper() == mb_ram_type.upper()]
        
        # 自动匹配：根据场景偏好找到最接近的单条容量型号
        prefer_size = scenario_info['prefer_single_mem']
        matched_mem_list = [m for m in phy_mem if get_val(m, 'capacity') == prefer_size]
        if not matched_mem_list: matched_mem_list = phy_mem 
        
        cm1, cm2 = st.columns([2, 1]) # 调宽按钮比例
        with cm1:
            mem = st.selectbox("选择内存型号", sorted(matched_mem_list, key=lambda x: get_val(x, 'price')), 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
        with cm2:
            single_cap = get_val(mem, 'capacity', 8)
            # 自动计算所需根数 = 建议总容量 / 单条容量
            rec_count = max(1, math.ceil(scenario_info["rec_ram"] / (single_cap if single_cap > 0 else 8)))
            # 数量加减按钮，上限绑定主板插槽
            mem_count = st.number_input("数量", min_value=1, max_value=mb_ram_slots, 
                                        value=min(int(rec_count), mb_ram_slots), step=1, key="mem_btn")

        # --- 5. 存储方案 (加减按钮 & 物理防冲突) ---
        st.subheader("存储方案推荐")
        st.success(f"💡 **建议：** 主盘 SSD **{scenario_info['main_ssd_rec']}**；副盘建议 **{scenario_info['sub_storage']}** ({scenario_info['sub_desc']})。")

        raw_storage = all_data.get('storage', {}).get('storage_devices', [])

        # 主硬盘部分
        cs1_m, cs2_m = st.columns([2, 1])
        with cs1_m:
            main_ssd = st.selectbox(
                "主存储 (NVMe SSD)", 
                [s for s in raw_storage if s.get('type') == 'SSD'], 
                format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}",
                key="ms_select"
            )
        with cs2_m:
            main_count = st.number_input(
                "主盘数量", 
                min_value=1, 
                max_value=int(mb_m2_slots), 
                value=1, 
                step=1, 
                key="main_count_btn",
                help=f"当前主板支持最多 {mb_m2_slots} 个 M.2 硬盘"
            )
            
        # 副硬盘部分
        cs1_s, cs2_s = st.columns([2, 1])
        with cs1_s:
            sub_storage = st.selectbox(
                f"副存储 ({scenario_info['sub_storage']})", 
                [s for s in raw_storage if s.get('type') == scenario_info['sub_storage']], 
                format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}",
                key="ss_select"
            )
        with cs2_s:
            remaining_slots = max(0, int(mb_max_drives) - main_count)
            sub_count = st.number_input(
                "副盘数量", 
                min_value=0, 
                max_value=remaining_slots, 
                value=0, 
                step=1, 
                key="sub_count_btn",
                help=f"基于总盘位限制，还可以选 {remaining_slots} 个"
            )

        if main_count + sub_count >= mb_max_drives:
            st.warning(f"⚠️ 存储接口已占满 ({mb_max_drives}/{mb_max_drives})")

    with col2:
        st.write("### ⚖️ 配置平衡性报告")
        total_p = (cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + 
                   (get_val(mem, 'price') * mem_count) + 
                   (get_val(main_ssd, 'price') * main_count) + 
                   (get_val(sub_storage, 'price') * sub_count))
        
        st.metric("方案总价", f"￥{total_p:.2f}")
        st.metric("预算剩余", f"￥{user_budget - total_p:.2f}", delta=f"{user_budget - total_p:.2f}")

        act_ram = get_val(mem, 'capacity', 0) * mem_count
        act_ssd = get_val(main_ssd, 'capacity', 0) * main_count
        
        st.markdown(f"""
        **配置清单摘要：**
        - **CPU**: {selected_cpu.get('model')}
        - **显卡**: {gpu.get('chipset')} ({gpu.get('brand')})
        - **主板**: {mb.get('model')}
        - **内存**: {act_ram}GB ({mb_ram_type} x{mem_count})
        - **插槽占用**: 内存 {mem_count}/{mb_ram_slots} | 硬盘 {main_count+sub_count}/{mb_max_drives}
        """)
        st.divider()

        if act_ram < scenario_info["rec_ram"]: st.error(f"❌ 内存容量低于建议 ({scenario_info['rec_ram']}G)")
        if get_val(mem, 'frequency') > mb_ram_freq: st.warning(f"⚠️ 内存频率超过主板支持，将降频运行")
        if act_ssd < scenario_info["main_ssd_val"]: st.error(f"❌ 主存储容量不足")
        if total_p > user_budget: st.error(f"💸 已超出总预算！")
        else: st.success("✅ 配置方案平衡且在预算内")

if __name__ == "__main__":
    main()
