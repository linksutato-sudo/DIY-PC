import streamlit as st
import json
import os

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 智能配置推荐器", layout="wide")
TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

# --- 数据加载 ---
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
        except Exception as e:
            st.error(f"加载 {filename} 失败: {e}")
            data[key] = {}
    return data

# --- 逻辑辅助函数 ---
def get_neighbor_tiers(base_tier):
    t_map = {t.lower(): t for t in TIERS_ORDER}
    formatted_tier = t_map.get(base_tier.lower(), "Mid")
    idx = TIERS_ORDER.index(formatted_tier)
    start = max(0, idx - 1)
    end = min(len(TIERS_ORDER), idx + 2)
    return [t.lower() for t in TIERS_ORDER[start:end]]

def get_val(item, key, default=0):
    val = item.get(key, default)
    if key == 'price':
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0
    return val

# --- 主程序 ---
def main():
    st.title("🖥️ DIY PC 智能预算动态推荐")
    
    all_data = load_data()
    if not all_data:
        return

    # --- 侧边栏配置 ---
    st.sidebar.header("核心预算设定")
    budget = st.sidebar.slider("总预算范围 (￥)", 2000, 50000, 8000, step=500)
    
    # 初始化 Session State 用于存储自动推荐的等级
    if 'current_tier' not in st.session_state:
        st.session_state.current_tier = "Mid"

    # 用户手动调整
    target_cpu_tier = st.sidebar.selectbox(
        "目标性能等级", 
        TIERS_ORDER, 
        index=TIERS_ORDER.index(st.session_state.current_tier),
        key="tier_selector"
    )
    st.session_state.current_tier = target_cpu_tier

    # --- 1. 筛选并初步排序 CPU (低价优先) ---
    all_cpus = []
    cpu_root = all_data.get('cpus', {})
    for brand_key in cpu_root:
        category = cpu_root[brand_key]
        if isinstance(category, list):
            all_cpus.extend([
                item for item in category 
                if item.get('tier', '').lower() == st.session_state.current_tier.lower()
            ])
    
    # CPU 也按价格低到高排序
    all_cpus = sorted(all_cpus, key=lambda x: get_val(x, 'price'))

    if not all_cpus:
        st.error(f"当前等级 {st.session_state.current_tier} 暂无数据。")
        return

    selected_cpu = st.selectbox(
        "确认 CPU 型号 (当前等级最廉选)", 
        all_cpus, 
        format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('model')}"
    )

    # --- 2. 匹配逻辑 (CPU/GPU 严格相等) ---
    cpu_tier_lower = selected_cpu.get('tier', st.session_state.current_tier).lower()
    allowed_gpu_tiers = [cpu_tier_lower]
    allowed_neighbor_tiers = get_neighbor_tiers(cpu_tier_lower)

    # --- 3. 筛选配件 (全部低价优先排序) ---
    # GPU
    available_gpus = sorted([
        g for g in all_data.get('gpus', {}).get('gpus', [])
        if g.get('tier', '').lower() in allowed_gpu_tiers
    ], key=lambda x: get_val(x, 'price'))

    # 主板
    socket = selected_cpu.get('socket')
    mb_series_data = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    matching_series_names = [s['series'] for s in mb_series_data if s['socket'] == socket]
    available_mbs = sorted([
        m for m in all_data.get('mb_models', {}).get('motherboard_models', [])
        if m['series'] in matching_series_names and m.get('tier', '').lower() in allowed_neighbor_tiers
    ], key=lambda x: get_val(x, 'price'))

    # 内存/硬盘
    available_mem = sorted([
        m for m in all_data.get('memory', {}).get('memory_modules', [])
        if m.get('tier', '').lower() in allowed_neighbor_tiers
    ], key=lambda x: get_val(x, 'price'))

    available_storage = sorted([
        s for s in all_data.get('storage', {}).get('storage_devices', [])
        if s.get('tier', '').lower() in allowed_neighbor_tiers
    ], key=lambda x: get_val(x, 'price'))

    # --- 4. 界面展示 ---
    if available_gpus and available_mbs:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("最优性价比组合推荐")
            gpu = st.selectbox("显卡选择 (严格匹配 CPU 等级)", available_gpus, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('brand')} {x.get('chipset')}")
            
            mb = st.selectbox("主板选择", available_mbs, 
                              format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('brand')} {x.get('model')}")
            
            num_mem = 2 if cpu_tier_lower in ["high-mid", "flagship"] else 1
            mem = st.selectbox(f"内存选择 (x{num_mem})", available_mem, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('display_name')}")
            
            ssd = st.selectbox("硬盘选择", available_storage, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('display_name')}")

        # --- 核心动态逻辑：根据冗余重荐 ---
        with col2:
            cpu_p = get_val(selected_cpu, 'price')
            total = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + (get_val(mem, 'price') * num_mem) + get_val(ssd, 'price')
            surplus = budget - total

            st.write("### 预算动态分析")
            st.metric("预估总价", f"￥{total:.2f}")
            st.metric("剩余冗余", f"￥{surplus:.2f}")

            # 寻找更高 Tier 的可能性
            current_idx = TIERS_ORDER.index(st.session_state.current_tier)
            if current_idx < len(TIERS_ORDER) - 1:
                next_tier = TIERS_ORDER[current_idx + 1]
                st.write(f"---")
                if surplus > 1000:  # 如果冗余超过 1000元，建议尝试升级
                    st.success(f"💡 预算充足！建议尝试升级至 **{next_tier}** 等级以获得更强性能。")
                    if st.button(f"一键升级至 {next_tier}"):
                        st.session_state.current_tier = next_tier
                        st.rerun()
                elif surplus < 0:
                    prev_tier = TIERS_ORDER[current_idx - 1]
                    st.warning(f"⚠️ 当前预算超支。建议降级至 **{prev_tier}**。")
                    if st.button(f"一键调整至 {prev_tier}"):
                        st.session_state.current_tier = prev_tier
                        st.rerun()

            st.write("---")
            st.write("**硬件摘要：**")
            st.write(f"- 等级状态: **{st.session_state.current_tier}**")
            st.write(f"- 接口: {selected_cpu.get('socket')}")
            st.caption(f"建议电源: {gpu.get('power_suggested', 500)}W")

    else:
        st.warning("🚨 匹配失败：可能是由于 Socket 限制或当前等级下显卡缺货。")
        if st.button("重置等级"):
            st.session_state.current_tier = "Mid"
            st.rerun()

if __name__ == "__main__":
    main()
