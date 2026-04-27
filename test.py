import streamlit as st
import json
import os
import math

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 场景化智能配置", layout="wide")

SCENARIOS = {
    "办公/家用 (Low/Entry)": {"min": 3000, "max":5500, "tier": "Low", "rec_ram": 16, "rec_ssd": 512},
    "主流网游 (Entry/Mid)": {"min": 5501, "max": 9000, "tier": "Mid", "rec_ram": 16, "rec_ssd": 1024},
    "3A游戏/2K竞技 (Mid/High-Mid)": {"min": 9001, "max": 18000, "tier": "High-Mid", "rec_ram": 32, "rec_ssd": 1024},
    "4K创作/深度学习 (High-Mid/Flagship)": {"min": 18001, "max": 25000, "tier": "Flagship", "rec_ram": 64, "rec_ssd": 2048},
    "顶级发烧/生产力 (Flagship+)": {"min": 25001, "max": 999999, "tier": "Flagship", "rec_ram": 128, "rec_ssd": 4096}
}

TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

def load_data():
    base_path = "data"
    files = {
        "cpus": "cpus.json",
        "gpus": "gpus.json",
        "memory": "memory_modules.json",
        "mb_models": "motherboard_models.json",
        "mb_series": "motherboards_series.json",
        "storage": "storage_devices.json"
    }
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
        return float(val) if key in ['price', 'pcie', 'capacity'] else val
    except:
        return 0

def main():
    st.title("🖥️ DIY PC 场景化平衡配置推荐")
    all_data = load_data()

    # --- 1. 预算 ---
    st.sidebar.header("第一步：设定预算")
    user_budget = st.sidebar.number_input("您的预算 (￥)", min_value=2000, max_value=1000000, value=6500, step=500)

    default_scenario = next(
        (name for name, info in SCENARIOS.items() if info["min"] <= user_budget <= info["max"]),
        "办公/家用 (Low/Entry)"
    )

    current_scenario = st.sidebar.selectbox(
        "当前匹配场景",
        list(SCENARIOS.keys()),
        index=list(SCENARIOS.keys()).index(default_scenario)
    )

    base_tier = SCENARIOS[current_scenario]["tier"]
    base_idx = TIERS_ORDER.index(base_tier) if base_tier in TIERS_ORDER else 0

    if base_tier == "Flagship":
        allowed_tiers = ["Flagship"]
    else:
        allowed_tiers = TIERS_ORDER[base_idx : min(base_idx + 2, len(TIERS_ORDER))]

    # ✅ 修复：切换场景时重置为最低档
    if 'prev_scenario' not in st.session_state or st.session_state.prev_scenario != current_scenario:
        st.session_state.manual_tier = allowed_tiers[0]
        st.session_state.prev_scenario = current_scenario

    if st.session_state.manual_tier not in allowed_tiers:
        st.session_state.manual_tier = allowed_tiers[0]

    # ✅ 修复：办公场景默认 Low
    if current_scenario == "办公/家用 (Low/Entry)":
        default_index = 0
    else:
        default_index = allowed_tiers.index(st.session_state.manual_tier)

    selected_tier = st.sidebar.selectbox(
        "性能等级微调",
        allowed_tiers,
        index=default_index
    )

    st.session_state.manual_tier = selected_tier

    scenario_info = SCENARIOS[current_scenario].copy()

    st.sidebar.info(f"💡 场景需求：{scenario_info['rec_ram']}GB 内存 | {scenario_info['rec_ssd']}GB 存储")

    # --- CPU ---
    cpu_data = all_data.get('cpus', {})
    available_cpus = []
    for brand in cpu_data:
        available_cpus.extend([
            item for item in cpu_data[brand]
            if item.get('tier', '').lower() == selected_tier.lower()
        ])

    if not available_cpus:
        for brand in cpu_data:
            available_cpus.extend(cpu_data[brand])
        available_cpus = sorted(available_cpus, key=lambda x: get_val(x, 'price'), reverse=True)[:10]

    selected_cpu = st.selectbox(
        "确认 CPU 型号",
        available_cpus,
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}"
    )

    cpu_p = get_val(selected_cpu, 'price')

    # --- GPU / 主板 ---
    all_gpus = all_data.get('gpus', {}).get('gpus', [])
    all_mb_models = all_data.get('mb_models', {}).get('motherboard_models', [])
    all_mb_series = all_data.get('mb_series', {}).get('Motherboard_Series', [])

    socket = selected_cpu.get('socket')

    series_map = {s['series']: s for s in all_mb_series if s['socket'] == socket}
    matching_series_names = list(series_map.keys())

    filtered_mbs = [m for m in all_mb_models if m['series'] in matching_series_names]

    gpu = st.selectbox(
        "选择显卡",
        sorted(all_gpus, key=lambda x: get_val(x, 'price')),
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}"
    )

    mb = st.selectbox(
        "选择主板",
        sorted(filtered_mbs, key=lambda x: get_val(x, 'price')),
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}"
    )

    current_mb_series_info = series_map.get(mb['series'], {})
    mb_ddr_type = current_mb_series_info.get('ddr', 'DDR4').upper()
    mb_pcie_ver = get_val(current_mb_series_info, 'pcie', 3.0)

    # --- 内存 ---
    raw_mem = all_data.get('memory', {}).get('memory_modules', [])
    supported_ddr = mb_ddr_type.split("/") if "/" in mb_ddr_type else [mb_ddr_type]

    available_mem = [m for m in raw_mem if m.get('type', '').upper() in supported_ddr]

    mem = st.selectbox(
        "选择内存型号",
        available_mem,
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}"
    )

    mem_count = st.number_input("内存数量", 1, 8, value=2)

    # --- SSD ---
    raw_ssd = all_data.get('storage', {}).get('storage_devices', [])
    available_ssd = [s for s in raw_ssd if get_val(s, 'pcie') <= mb_pcie_ver]

    ssd = st.selectbox(
        "选择硬盘型号",
        available_ssd,
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}"
    )

    ssd_count = st.number_input("硬盘数量", 1, 4, value=1)

    # --- 价格 ---
    total = (
        cpu_p
        + get_val(gpu, 'price')
        + get_val(mb, 'price')
        + get_val(mem, 'price') * mem_count
        + get_val(ssd, 'price') * ssd_count
    )

    st.sidebar.metric("总价", f"￥{total:.0f}")
    st.sidebar.metric("剩余预算", f"￥{user_budget - total:.0f}")

if __name__ == "__main__":
    main()
