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
    """获取与 base_tier 相同或相邻的等级列表（用于主板、内存等配件）"""
    t_map = {t.lower(): t for t in TIERS_ORDER}
    formatted_tier = t_map.get(base_tier.lower(), "Mid")
    
    idx = TIERS_ORDER.index(formatted_tier)
    start = max(0, idx - 1)
    end = min(len(TIERS_ORDER), idx + 2)
    return [t.lower() for t in TIERS_ORDER[start:end]]

def get_val(item, key, default=0):
    """通用安全取值函数，确保价格返回数字"""
    val = item.get(key, default)
    if key == 'price':
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0
    return val

# --- 主程序 ---
def main():
    st.title("🖥️ DIY PC 智能配置推荐 (GPU 低价优先版)")
    
    all_data = load_data()
    if not all_data:
        return

    # --- 侧边栏配置 ---
    st.sidebar.header("核心配置")
    target_cpu_tier = st.sidebar.selectbox("第一步：选择 CPU 性能等级", TIERS_ORDER, index=2)
    budget = st.sidebar.slider("预算参考 (￥)", 2000, 50000, 8000, step=500)
    
    # --- 1. 筛选 CPU ---
    all_cpus = []
    cpu_root = all_data.get('cpus', {})
    for brand_key in cpu_root:
        category = cpu_root[brand_key]
        if isinstance(category, list):
            all_cpus.extend([
                item for item in category 
                if item.get('tier', '').lower() == target_cpu_tier.lower()
            ])

    if not all_cpus:
        st.error(f"库中没有等级为 {target_cpu_tier} 的 CPU，请检查数据。")
        return

    selected_cpu = st.selectbox(
        "确认 CPU 型号", 
        all_cpus, 
        format_func=lambda x: f"{x.get('model')} - ￥{get_val(x, 'price')}"
    )

    # --- 2. 匹配逻辑核心 ---
    cpu_tier_lower = selected_cpu.get('tier', target_cpu_tier).lower()
    # 显卡逻辑：强制要求 Tier 严格相等
    allowed_gpu_tiers = [cpu_tier_lower]
    # 其他配件逻辑：允许相邻等级
    allowed_neighbor_tiers = get_neighbor_tiers(cpu_tier_lower)
    
    st.info(f"✅ 已选 CPU: {selected_cpu.get('model')} ({cpu_tier_lower.upper()})")

    # --- 3. 筛选并排序配件 ---
    # 显卡：严格匹配 + 【按价格升序排序】
    available_gpus = [
        g for g in all_data.get('gpus', {}).get('gpus', [])
        if g.get('tier', '').lower() in allowed_gpu_tiers
    ]
    # 核心修改：使用 sorted 函数对 GPU 进行价格排序
    available_gpus = sorted(available_gpus, key=lambda x: get_val(x, 'price'))

    # 主板：Socket 匹配 + 相邻 Tier 匹配 + 按价格排序
    socket = selected_cpu.get('socket')
    mb_series_data = all_data.get('mb_series', {}).get('Motherboard_Series', [])
    matching_series_names = [s['series'] for s in mb_series_data if s['socket'] == socket]
    available_mbs = [
        m for m in all_data.get('mb_models', {}).get('motherboard_models', [])
        if m['series'] in matching_series_names and m.get('tier', '').lower() in allowed_neighbor_tiers
    ]
    available_mbs = sorted(available_mbs, key=lambda x: get_val(x, 'price'))

    # 内存与硬盘：相邻 Tier 匹配 + 按价格排序
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
            st.subheader("组件选择")
            gpu = st.selectbox("第二步：选择显卡 (低价优先)", available_gpus, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('brand')} {x.get('chipset')} ({x.get('tier')})")
            
            mb = st.selectbox("第三步：选择主板", available_mbs, 
                              format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('brand')} {x.get('model')}")
            
            num_mem = 2 if cpu_tier_lower in ["high-mid", "flagship"] else 1
            mem = st.selectbox(f"第四步：选择内存 (数量: {num_mem})", available_mem, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('display_name')}")
            
            ssd = st.selectbox("第五步：选择硬盘", available_storage, 
                               format_func=lambda x: f"￥{get_val(x, 'price')} - {x.get('display_name')}")

        with col2:
            # 计算总价
            cpu_p = get_val(selected_cpu, 'price')
            gpu_p = get_val(gpu, 'price')
            mb_p = get_val(mb, 'price')
            mem_p = get_val(mem, 'price') * num_mem
            ssd_p = get_val(ssd, 'price')
            
            total = cpu_p + gpu_p + mb_p + mem_p + ssd_p
            
            st.write("### 价格概览")
            st.metric("当前配置总价", f"￥{total:.2f}")
            st.metric("预算剩余", f"￥{budget - total:.2f}", delta_color="normal")
            
            if total > budget:
                st.error(f"已超出预算 ￥{total - budget:.2f}")
            else:
                st.success("✅ 性能对等且符合预算")
            
            st.write("---")
            st.write("**硬件规格摘要：**")
            st.write(f"- 接口类型: {socket}")
            st.write(f"- 显存大小: {gpu.get('vram', 'N/A')}")
            st.caption(f"💡 建议电源额定功率: {gpu.get('power_suggested', 500)}W 以上")

    else:
        st.warning("🚨 匹配失败：当前选择无法找到完全平衡的 GPU 或兼容的主板。")

if __name__ == "__main__":
    main()
