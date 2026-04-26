import streamlit as st
import json
import os
import random

# 配置页面
st.set_page_config(page_title="DIY PC 组装推荐器", layout="wide")

# 数据加载函数
def load_data():
    base_path = "data"
    files = {
        "cpus": "cpus.json",
        "gpus": "gpus.json", # 注意你提到的文件名是 gpus.jison，这里建议统一为 .json
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
        except FileNotFoundError:
            st.error(f"找不到文件: {path}")
            data[key] = {}
    return data

# 获取相邻 Tier 的逻辑
def get_compatible_tiers(selected_tier):
    tiers = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]
    try:
        idx = tiers.index(selected_tier)
        # 返回当前等级及其前后一个等级
        start_idx = max(0, idx - 1)
        end_idx = min(len(tiers), idx + 2)
        return [t.lower() for t in tiers[start_idx:end_idx]]
    except ValueError:
        return [selected_tier.lower()]

# 主程序
def main():
    st.title("🖥️ DIY PC 智能配置推荐")
    
    all_data = load_data()
    if not all_data:
        return

    # --- 侧边栏配置 ---
    st.sidebar.header("配置偏好")
    target_tier = st.sidebar.selectbox("选择目标性能等级 (Tier)", 
                                     ["Low", "Entry", "Mid", "High-Mid", "Flagship"])
    
    budget = st.sidebar.slider("预算范围 (￥)", 2000, 50000, 8000, step=500)
    
    # 允许的 Tier 范围列表（转换为小写进行匹配）
    allowed_tiers = get_compatible_tiers(target_tier)

    # --- 过滤逻辑 ---
    # 1. 过滤 CPU
    # 注意：cpus.json 结构里包含 Intel_Processors 和可能存在的 AMD 列表
    all_cpus = []
    for brand in all_data['cpus']:
        all_cpus.extend([item for item in all_data['cpus'][brand] 
                        if item.get('tier', '').lower() in allowed_tiers])

    if not all_cpus:
        st.warning("当前等级下没有找到匹配的 CPU")
        return

    # 用户手动选择或随机推荐一个核心
    selected_cpu = st.selectbox("选择 CPU", all_cpus, format_func=lambda x: f"{x['model']} ({x['tier']}) - ￥{x['price']}")

    # 2. 匹配主板系列 (根据 CPU Socket)
    socket = selected_cpu.get('socket')
    matching_series = [s['series'] for s in all_data['mb_series']['Motherboard_Series'] 
                       if s['socket'] == socket]

    # 3. 过滤主板型号
    available_mbs = [m for m in all_data['mb_models']['motherboard_models'] 
                     if m['series'] in matching_series and m.get('tier', '').lower() in allowed_tiers]
    
    if not available_mbs:
        st.info("按型号库匹配失败，尝试根据芯片组系列推荐。")
        # 如果 model 库没匹配到，构造一个虚拟条目（基于 series 库价格）
        available_mbs = [{"model": f"通用 {selected_cpu['supported_motherboards']} 主板", "price": 500, "brand": "通用"}]

    # 4. 过滤 GPU
    available_gpus = [g for g in all_data['gpus']['gpus'] 
                      if g.get('tier', '').lower() in allowed_tiers]

    # 5. 内存与硬盘 (根据 Tier 决定数量)
    num_mem = 2 if target_tier in ["High-Mid", "Flagship"] else 1
    num_ssd = 2 if target_tier == "Flagship" else 1
    
    available_mem = [m for m in all_data['memory']['memory_modules'] 
                     if m.get('tier', '').lower() in allowed_tiers]
    
    available_storage = [s for s in all_data['storage']['storage_devices'] 
                         if s.get('tier', '').lower() in allowed_tiers]

    # --- 最终展示与计算 ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("推荐清单")
        
        # 简单选择器逻辑
        mb = st.selectbox("选择主板", available_mbs, format_func=lambda x: f"{x['brand']} {x['model']} - ￥{x['price']}")
        gpu = st.selectbox("选择显卡", available_gpus, format_func=lambda x: f"{x['brand']} {x['chipset']} - ￥{x['price']}")
        mem = st.selectbox(f"选择内存 (将购买 {num_mem} 条)", available_mem, format_func=lambda x: f"{x['display_name']} - ￥{x['price']}")
        ssd = st.selectbox(f"选择硬盘 (将购买 {num_ssd} 条)", available_storage, format_func=lambda x: f"{x['display_name']} - ￥{x['price']}")

        total_price = selected_cpu['price'] + mb['price'] + gpu['price'] + (mem['price'] * num_mem) + (ssd['price'] * num_ssd)

    with col2:
        st.metric("预估总价", f"￥{total_price}")
        if total_price > budget:
            st.error(f"超出预算: ￥{total_price - budget}")
        else:
            st.success("配置在预算范围内！")
            
        st.write("### 性能详情")
        st.write(f"- **核心数**: {selected_cpu['specs']}")
        st.write(f"- **显存**: {gpu['vram']}")
        st.write(f"- **总内存**: {mem['capacity'] * num_mem} GB")
        st.write(f"- **总存储**: {ssd['capacity'] * num_ssd} GB")

    st.divider()
    st.caption("注：以上价格为库内参考价。组装电脑还需考虑机箱、散热器及电源（建议额定功率: {}W 以上）。".format(gpu.get('power_suggested', 500)))

if __name__ == "__main__":
    main()
