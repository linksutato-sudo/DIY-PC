import streamlit as st
import json
import os

# --- 配置页面 ---
st.set_page_config(page_title="DIY PC 智能组装推荐器", layout="wide")

# --- 全局常量 ---
TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

# --- 数据加载函数 ---
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
        except FileNotFoundError:
            st.error(f"找不到文件: {path}")
            data[key] = {}
        except Exception as e:
            st.error(f"解析 {filename} 出错: {e}")
            data[key] = {}
    return data

# --- 核心逻辑函数 ---
TIERS_ORDER = ["Low", "Entry", "Mid", "High-Mid", "Flagship"]

def get_neighbor_tiers(base_tier):
    """获取与 base_tier 相同或相邻的等级列表"""
    # 统一转为首字母大写以匹配列表
    base_tier = base_tier.capitalize() if base_tier.lower() != "high-mid" else "High-Mid"
    
    if base_tier not in TIERS_ORDER:
        return [base_tier.lower()]
    
    idx = TIERS_ORDER.index(base_tier)
    start = max(0, idx - 1)
    end = min(len(TIERS_ORDER), idx + 2)
    # 返回小写列表用于后续匹配
    return [t.lower() for t in TIERS_ORDER[start:end]]

def safe_get_price(item, keys=['price', 'tray_price']):
    """从多个可能的键中安全获取数字价格"""
    for key in keys:
        p = item.get(key)
        if isinstance(p, (int, float)):
            return p
    return 0

# --- 主程序 ---
def main():
    # ... 前面加载数据的代码保持不变 ...
    all_data = load_data()
    
    st.sidebar.header("核心配置")
    # 1. 用户先选 CPU 等级
    target_cpu_tier = st.sidebar.selectbox("选择 CPU 性能等级", TIERS_ORDER)
    
    # 2. 筛选并选择 CPU
    all_cpus = []
    for brand in all_data.get('cpus', {}):
        # 严格匹配用户选的 CPU Tier
        all_cpus.extend([item for item in all_data['cpus'][brand] 
                         if item.get('tier', '').lower() == target_cpu_tier.lower()])

    if not all_cpus:
        st.error(f"库中没有等级为 {target_cpu_tier} 的 CPU，请检查数据或更换选项。")
        return

    selected_cpu = st.selectbox(
        "第一步：确认 CPU 型号", 
        all_cpus, 
        format_func=lambda x: f"{x.get('model')} - ￥{x.get('tray_price', '无报价')}"
    )

    # 3. 根据选定的 CPU Tier，计算允许的 GPU/主板/内存 Tier
    cpu_actual_tier = selected_cpu.get('tier', target_cpu_tier)
    allowed_neighbor_tiers = get_neighbor_tiers(cpu_actual_tier)
    
    st.info(f"已选 CPU 等级: {cpu_actual_tier}。将为您匹配相邻等级 ({', '.join(allowed_neighbor_tiers)}) 的配件。")

    # 4. 筛选显卡 (GPU Tier 必须在 CPU 的相邻范围内)
    available_gpus = [
        g for g in all_data.get('gpus', {}).get('gpus', [])
        if g.get('tier', '').lower() in allowed_neighbor_tiers
    ]

    # 5. 筛选主板 (主板 Tier 也建议在相邻范围内，且 Socket 必须匹配)
    socket = selected_cpu.get('socket')
    matching_series = [
        s['series'] for s in all_data['mb_series']['Motherboard_Series'] 
        if s['socket'] == socket
    ]
    
    available_mbs = [
        m for m in all_data['mb_models']['motherboard_models']
        if m['series'] in matching_series and m.get('tier', '').lower() in allowed_neighbor_tiers
    ]

    # --- 界面展示 (使用安全 get 避免 KeyError) ---
    if available_gpus and available_mbs:
        gpu = st.selectbox("第二步：选择显卡", available_gpus, 
                           format_func=lambda x: f"{x.get('brand')} {x.get('chipset')} ({x.get('tier')}) - ￥{x.get('price', 0)}")
        
        mb = st.selectbox("第三步：选择主板", available_mbs, 
                          format_func=lambda x: f"{x.get('brand')} {x.get('model')} ({x.get('tier')}) - ￥{x.get('price', 0)}")
        
        # 内存和硬盘同样使用 allowed_neighbor_tiers 过滤...
        # (此处省略相似的内存/硬盘 selectbox 代码)
        
        # 价格计算核心防错
        def safe_price(item, key='price'):
            p = item.get(key, 0)
            return p if isinstance(p, (int, float)) else 0

        total = safe_price(selected_cpu, 'tray_price') + safe_price(gpu) + safe_price(mb)
        st.header(f"配置总价: ￥{total}")
    else:
        st.warning("未能找到兼容的显卡或主板，请尝试调整 CPU 等级。")
        
    col1, col2 = st.columns([2, 1])

    with col1:
        st.write("### 选择其他配件")
        
        gpu = st.selectbox("第二步：选择显卡", available_gpus, 
                           format_func=lambda x: f"{x.get('brand')} {x.get('chipset')} ({x.get('tier')}) - ￥{safe_get_price(x)}")
        
        mb = st.selectbox("第三步：选择主板", available_mbs, 
                          format_func=lambda x: f"{x.get('brand')} {x.get('model')} ({x.get('tier')}) - ￥{safe_get_price(x)}")
        
        # 数量逻辑
        num_mem = 2 if target_cpu_tier in ["High-Mid", "Flagship"] else 1
        num_ssd = 2 if target_cpu_tier == "Flagship" else 1
        
        mem = st.selectbox(f"第四步：选择内存 (数量: {num_mem})", available_mem, 
                           format_func=lambda x: f"{x.get('display_name')} - ￥{safe_get_price(x)}")
        
        ssd = st.selectbox(f"第五步：选择硬盘 (数量: {num_ssd})", available_storage, 
                           format_func=lambda x: f"{x.get('display_name')} - ￥{safe_get_price(x)}")

    # --- 6. 价格与统计 ---
    with col2:
        cpu_p = safe_get_price(selected_cpu, ['price', 'tray_price'])
        gpu_p = safe_get_price(gpu)
        mb_p = safe_get_price(mb)
        mem_p = safe_get_price(mem) * num_mem
        ssd_p = safe_get_price(ssd) * num_ssd
        
        total_price = cpu_p + gpu_p + mb_p + mem_p + ssd_p

        st.write("### 配置单概览")
        st.metric("预估总价", f"￥{total_price}")
        
        if total_price > budget:
            st.error(f"已超过预算: ￥{total_price - budget}")
        else:
            st.success("当前配置在预算内！")

        st.write("---")
        st.write("**配置详情：**")
        st.write(f"- CPU 核心: {selected_cpu.get('specs', '未知')}")
        st.write(f"- 显存: {gpu.get('vram', '未知')}")
        st.write(f"- 内存总量: {mem.get('capacity', 0) * num_mem} GB")
        st.write(f"- 存储总量: {ssd.get('capacity', 0) * num_ssd} GB")
        
        st.caption(f"建议电源: {gpu.get('power_suggested', 500)}W 以上")

    st.divider()
    st.info("💡 温馨提示：本工具仅提供核心组件匹配。装机时请务必确认机箱尺寸是否支持显卡长度，以及散热器是否兼容 CPU 扣具。")

if __name__ == "__main__":
    main()
