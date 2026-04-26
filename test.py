import streamlit as st
import json
import os

# 设置页面配置
st.set_page_config(page_title="DIY PC 组装推荐器", layout="wide")

# --- 数据加载函数 ---
def load_data():
    data_path = "data"
    files = {
        "cpus": "cpus.json",
        "gpus": "gpus.json",
        "memory": "memory_modules.json",
        "motherboard_models": "motherboard_models.json",
        "storage": "storage_devices.json"
    }
    loaded_data = {}
    for key, filename in files.items():
        path = os.path.join(data_path, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded_data[key] = json.load(f)
        except FileNotFoundError:
            st.error(f"找不到文件: {path}")
            loaded_data[key] = {}
    return loaded_data

data = load_data()

# --- 辅助函数：提取列表 ---
def get_list_by_tier(data_list, tier):
    # 统一转为小写比较，增加鲁棒性
    return [item for item in data_list if item.get('tier', '').lower() == tier.lower()]

# --- UI 界面 ---
st.title("🖥️ DIY PC 智能配置推荐")
st.sidebar.header("选择你的需求")

# 1. 选择档次 (Tier)
# 注意：根据你的数据，Tier 有 Low, Mid, High, Flagship, high-mid 等
tier_options = ["Low", "Mid", "High", "Flagship"]
selected_tier = st.sidebar.selectbox("选择电脑档次/使用场景", tier_options)

st.subheader(f"当前方案：{selected_tier} 级别配置")

# --- 核心逻辑：筛选配件 ---
# CPU 处理 (Intel_Processors 为键名)
cpu_pool = data['cpus'].get('Intel_Processors', [])
filtered_cpus = get_list_by_tier(cpu_pool, selected_tier)

# GPU 处理
gpu_pool = data['gpus'].get('gpus', [])
filtered_gpus = get_list_by_tier(gpu_pool, selected_tier)

# 内存处理
mem_pool = data['memory'].get('memory_modules', [])
filtered_mem = get_list_by_tier(mem_pool, selected_tier)

# 主板处理
mobo_pool = data['motherboard_models'].get('motherboard_models', [])
filtered_mobo = get_list_by_tier(mobo_pool, selected_tier)

# 硬盘处理
storage_pool = data['storage'].get('storage_devices', [])
filtered_storage = get_list_by_tier(storage_pool, selected_tier)

# --- 渲染选择器 ---
col1, col2 = st.columns(2)

with col1:
    st.write("### 核心三大件")
    # CPU
    selected_cpu = st.selectbox("选择处理器 (CPU)", filtered_cpus, format_func=lambda x: f"{x['model']} - ￥{x['tray_price']}") if filtered_cpus else None
    
    # GPU
    selected_gpu = st.selectbox("选择显卡 (GPU)", filtered_gpus, format_func=lambda x: f"{x['brand']} {x['chipset']} - ￥{x['price']}") if filtered_gpus else None
    
    # 主板
    selected_mobo = st.selectbox("选择主板", filtered_mobo, format_func=lambda x: f"{x['brand']} {x['model']} - ￥{x['price']}") if filtered_mobo else None

with col2:
    st.write("### 存储与扩展")
    # 内存
    selected_mem = st.selectbox("选择内存", filtered_mem, format_func=lambda x: f"{x['display_name']} - ￥{x['price']}") if filtered_mem else None
    mem_count = st.number_input("内存数量", min_value=1, max_value=4, value=2 if selected_tier in ["High", "Flagship"] else 1)
    
    # 硬盘
    selected_storage = st.selectbox("选择硬盘", filtered_storage, format_func=lambda x: f"{x['display_name']} - ￥{x['price']}") if filtered_storage else None
    storage_count = st.number_input("硬盘数量", min_value=1, max_value=4, value=1)

# --- 价格计算与清单汇总 ---
st.divider()

total_price = 0
items = []

if selected_cpu:
    total_price += selected_cpu['tray_price']
    items.append({"部件": "处理器 (CPU)", "型号": selected_cpu['model'], "单价": selected_cpu['tray_price'], "数量": 1})

if selected_gpu:
    total_price += selected_gpu['price']
    items.append({"部件": "显卡 (GPU)", "型号": selected_gpu['chipset'], "单价": selected_gpu['price'], "数量": 1})

if selected_mobo:
    total_price += selected_mobo['price']
    items.append({"部件": "主板", "型号": selected_mobo['model'], "单价": selected_mobo['price'], "数量": 1})

if selected_mem:
    m_price = selected_mem['price'] * mem_count
    total_price += m_price
    items.append({"部件": "内存", "型号": selected_mem['model'], "单价": selected_mem['price'], "数量": mem_count})

if selected_storage:
    s_price = selected_storage['price'] * storage_count
    total_price += s_price
    items.append({"部件": "硬盘", "型号": selected_storage['model'], "单价": selected_storage['price'], "数量": storage_count})

# 展示配置单表格
if items:
    st.table(items)
    st.metric(label="预计总金额", value=f"￥{total_price:,.2f}")
else:
    st.warning("该档次下部分配件库数据为空，请检查 JSON 文件的 tier 标签。")

# 额外建议
if selected_gpu and selected_gpu.get('power_suggested'):
    st.info(f"💡 建议电源功率：至少 {selected_gpu['power_suggested']}W")
