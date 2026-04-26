import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 1. 页面基本设置 ---
st.set_page_config(page_title="DIY-PC 装机助手", page_icon="🖥️", layout="wide")

# --- 2. 强力数据加载函数 ---
def safe_load(file_name):
    """尝试从当前目录或data目录加载JSON，失败返回空字典"""
    paths = [file_name, os.path.join("data", file_name)]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                continue
    return {}

@st.cache_data
def get_data():
    raw_data = {
        "cpus": safe_load("cpus.json"),
        "m_series": safe_load("motherboards_series.json"),
        "m_models": safe_load("motherboard_models.json"),
        "memory": safe_load("memory_modules.json"),
        "storage": safe_load("storage_devices.json")
    }
    
    # 针对 memory_modules.json 的特殊结构进行提取
    # 你的 JSON 结构是 {"memory_modules": [ { "key": {...} } ]}
    mem_pool = {}
    if "memory_modules" in raw_data["memory"]:
        content = raw_data["memory"]["memory_modules"]
        if isinstance(content, list) and len(content) > 0:
            mem_pool = content[0] # 拿到列表里的第一个字典
    raw_data["mem_pool"] = mem_pool
    
    # 运行打标签逻辑
    if "motherboard_models" in raw_data["m_models"]:
        add_tags_to_motherboards(raw_data["m_models"])
        
    return raw_data

all_data = get_data()

# --- 3. 界面逻辑 ---
st.title("🖥️ DIY-PC 硬件导购系统")

# 检查基础数据是否存在，防止完全空白
if not all_data["cpus"] or "Intel_Processors" not in all_data["cpus"]:
    st.error("无法加载硬件数据，请检查 JSON 文件是否在正确位置！")
    st.stop()

# 初始化总价
total_price = 0
sidebar_summary = []

# --- 步骤 1: CPU ---
st.header("1. 选择处理器")
col_cpu1, col_cpu2 = st.columns([1, 2])
with col_cpu1:
    brand = st.radio("平台", ["Intel", "AMD"], horizontal=True)
    cpu_list = all_data["cpus"].get("Intel_Processors", []) if brand == "Intel" else all_data["cpus"].get("AMD_Processors", [])
    cpu_model = st.selectbox("选择型号", [c["model"] for c in cpu_list])

selected_cpu = next(c for c in cpu_list if c["model"] == cpu_model)
cpu_p = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
total_price += cpu_p
sidebar_summary.append(f"CPU: {cpu_model} (￥{cpu_p})")

with col_cpu2:
    st.info(f"**接口**: {selected_cpu['socket']} | **参数**: {selected_cpu['specs']}")
    st.metric("价格", f"￥{cpu_p}")

# --- 步骤 2: 主板 ---
st.header("2. 选择主板")
# 获取兼容系列
m_series_list = all_data["m_series"].get("Motherboard_Series", [])
compat_series = [s["series"] for s in m_series_list if s["socket"] == selected_cpu["socket"]]
# 获取兼容型号
m_models_list = all_data["m_models"].get("motherboard_models", [])
compat_boards = [b for b in m_models_list if b["series"] in compat_series]

if not compat_boards:
    st.warning("未找到匹配的主板")
    selected_board = None
else:
    col_mb1, col_mb2 = st.columns([1, 2])
    with col_mb1:
        board_name = st.selectbox("兼容主板", [f"{b['brand']} {b['model']}" for b in compat_boards])
        selected_board = next(b for b in compat_boards if f"{b['brand']} {b['model']}" == board_name)
    with col_mb2:
        tags = selected_board.get("tags", [])
        st.markdown(" ".join([f"`{t}`" for t in tags]))
        st.metric("价格", f"￥{selected_board['price']}")
        total_price += selected_board['price']
        sidebar_summary.append(f"主板: {selected_board['model']} (￥{selected_board['price']})")

# --- 步骤 3: 内存 ---
st.header("3. 选择内存")
if selected_board:
    # 兼容性：检测主板是否有 DDR4 标签
    is_d4 = "DDR4" in selected_board.get("tags", [])
    req_type = "DDR4" if is_d4 else "DDR5"
    
    # 从处理后的 mem_pool 中筛选
    mem_items = [m for m in all_data["mem_pool"].values() if m.get("type") == req_type]
    
    if mem_items:
        col_m1, col_m2 = st.columns([1, 2])
        with col_m1:
            m_name = st.selectbox(f"匹配的 {req_type} 内存", [m["display_name"] for m in mem_items])
            selected_mem = next(m for m in mem_items if m["display_name"] == m_name)
        with col_m2:
            st.write(f"规格: {selected_mem['frequency']}MHz | 容量: {selected_mem['capacity']}G")
            st.metric("价格", f"￥{selected_mem['price']}")
            total_price += selected_mem['price']
            sidebar_summary.append(f"内存: {selected_mem['display_name']} (￥{selected_mem['price']})")
    else:
        st.warning(f"缺少 {req_type} 内存数据")

# --- 侧边栏汇总 ---
st.sidebar.title("🛒 配置清单")
for item in sidebar_summary:
    st.sidebar.write(item)
st.sidebar.markdown("---")
st.sidebar.subheader(f"总计: :red[￥{total_price}]")
