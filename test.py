import streamlit as st
import json
import os

# --- 全局配置 ---
st.set_page_config(page_title="DIY PC 智能配置推荐", layout="wide")
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
    """获取与 base_tier 相同或相邻的等级列表（用于主板、内存等配件）"""
    # 格式化字符串以匹配 TIERS_ORDER
    t_map = {t.lower(): t for t in TIERS_ORDER}
    formatted_tier = t_map.get(base_tier.lower(), "Mid")
    
    idx = TIERS_ORDER.index(formatted_tier)
    start = max(0, idx - 1)
    end = min(len(TIERS_ORDER), idx + 2)
    return [t.lower() for t in TIERS_ORDER[start:end]]

def safe_price(item, keys=['price', 'tray_price']):
    """安全获取数字价格"""
    for k in keys:
        p = item.get(k, 0)
        if isinstance(p, (int, float)):
            return p
    return 0

# --- 主程序 ---
def main():
    st.title("🖥️ DIY PC 智能配置推荐 (严格平衡版)")
    
    all_data = load_data()
    if not all_data:
        return

    # --- 侧边栏配置 ---
    st.sidebar.header("核心配置")
    target_cpu_tier = st.sidebar.selectbox("第一步：选择 CPU 性能等级", TIERS_ORDER, index=2)
    budget = st.sidebar.slider("预算参考 (￥)", 2000, 50000, 8000, step=500)
    
    # --- 1. 筛选 CPU ---
    all_cpus = []
    for brand in all_data.get('cpus', {}):
        all_cpus.extend([
            item for item in all_data['cpus'][brand] 
            if item.get('tier', '').lower() == target_cpu_tier.lower()
        ])

    if not all_cpus:
        st.error(f"库中没有等级为 {target_cpu_tier} 的 CPU，请检查数据。")
        return

    selected_cpu = st.selectbox(
        "确认 CPU 型号", 
        all_cpus, 
        format_func=lambda x: f"{x.get('model')} - ￥{safe_price(x, ['tray_price', 'price'])}"
    )

    # --- 2. 匹配逻辑核心 ---
    cpu_tier_lower = selected_cpu.get('tier', target_cpu_tier).lower()
    # 显卡逻辑：严格相等
    allowed_gpu_tiers = [cpu_tier_lower]
    # 其他配件逻辑：相邻等级
    allowed_neighbor_tiers = get_neighbor_tiers(cpu_tier_lower)
    
    st.info(f"✅ 已选 CPU: {selected_cpu['model']} ({cpu_tier_lower.upper()})")
    st.caption(f"匹配规则：显卡需严格对应 {cpu_tier_lower.upper()} 等级；其他配件允许在 {', '.join(allowed_neighbor_tiers)} 范围内。")

    # --- 3. 筛选配件 ---
    # 显卡 (严格匹配 CPU Tier)
    available_gpus = [
        g for g in all_data.get('gpus', {}).get('gpus', [])
        if g.get('tier', '').lower() in allowed_gpu_tiers
    ]

    # 主板 (Socket 匹配 + 相邻 Tier 匹配)
    socket = selected_cpu.get('socket')
    matching_series = [
        s['series'] for s in all_data.get('mb_series', {}).get('Motherboard_Series', []) 
        if s['socket'] == socket
    ]
    available_mbs = [
        m for m in all_data.get('mb_models', {}).get('motherboard_models', [])
        if m['series'] in matching_series and m.get('tier', '').lower() in allowed_neighbor_tiers
    ]

    # 内存与硬盘
    available_mem = [
        m for m in all_data.get('memory', {}).get('memory_modules', [])
        if m.get('tier', '').lower() in allowed_neighbor_tiers
    ]
    available_storage = [
        s for s in all_data.get('storage', {}).get('storage_devices', [])
        if s.get('tier', '').lower() in allowed_neighbor_tiers
    ]

    # --- 4. 界面展示 ---
    if available_gpus and available_mbs:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            gpu = st.selectbox("第二步：选择显卡 (严格对等)", available_gpus, 
                               format_func=lambda x: f"{x.get('brand')} {x.get('chipset')} - ￥{safe_price(x)}")
            
            mb = st.selectbox("第三步：选择主板 (兼容范围)", available_mbs, 
                              format_func=lambda x: f"{x.get('brand')} {x.get('model')} - ￥{safe_price(x)}")
            
            num_mem = 2 if cpu_tier_lower in ["high-mid", "flagship"] else 1
            mem = st.selectbox(f"第四步：选择内存 (数量: {num_mem})", available_mem, 
                               format_func=lambda x: f"{x.get('display_name')} - ￥{safe_price(x)}")
            
            ssd = st.selectbox("第五步：选择硬盘", available_storage, 
                               format_func=lambda x: f"{x.get('display_name')} - ￥{safe_price(x)}")

        with col2:
            total = (safe_price(selected_cpu, ['tray_price', 'price']) + 
                     safe_price(gpu) + safe_price(mb) + 
                     (safe_price(mem) * num_mem) + safe_price(ssd))
            
            st.metric("预算参考", f"￥{budget}")
            st.metric("当前总价", f"￥{total}", delta=f"{budget - total} (余)" if budget >= total else f"{budget - total} (超)")
            
            if total > budget:
                st.error("❌ 当前配置超出预算，请考虑降低 CPU 等级或调整配件。")
            else:
                st.success("✅ 配置合理，性能均衡！")
            
            st.write("---")
            st.write("**硬件摘要：**")
            st.write(f"- 平台: {socket}")
            st.write(f"- 显存: {gpu.get('vram', 'N/A')}")
            st.caption(f"建议电源: {gpu.get('power_suggested', 500)}W")

    else:
        st.warning("🚨 在当前严格匹配规则下，未能找到兼容的显卡或主板，请检查数据库或尝试其他 CPU。")

if __name__ == "__main__":
    main()
