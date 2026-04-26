import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 配置页面 ---
st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️", layout="wide")

# --- 健壮的数据加载函数 ---
def safe_load_json(file_name):
    """同时尝试根目录和data目录读取文件"""
    possible_paths = [file_name, os.path.join("data", file_name)]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_combined_data():
    data = {
        "cpus": safe_load_json("cpus.json"),
        "m_series": safe_load_json("motherboards_series.json"),
        "m_models": safe_load_json("motherboard_models.json"),
        "memory": safe_load_json("memory_modules.json"),
        "storage": safe_load_json("storage_devices.json")
    }
    
    # 核心修复：处理 memory_modules 的特殊嵌套结构
    # 你的 JSON 是 {"memory_modules": [ { "key": {...} } ]}
    if data["memory"] and isinstance(data["memory"].get("memory_modules"), list):
        # 提取列表中的第一个字典
        data["memory_pool"] = data["memory"]["memory_modules"][0]
    else:
        data["memory_pool"] = {}

    # 运行 tagger 为主板添加标签
    if data["m_models"]:
        add_tags_to_motherboards(data["m_models"])
    
    return data

all_data = get_combined_data()

# --- 界面展示 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not all_data["cpus"] or not all_data["m_models"]:
    st.error("❌ 无法加载 JSON 数据，请确保 .json 文件与 app.py 在同一目录或 data 目录下。")
else:
    # 侧边栏：配置单统计
    st.sidebar.title("📑 我的配置单")
    summary_price = 0

    # 1. CPU 选择
    st.header("1. 处理器 (CPU)")
    brand = st.radio("选择阵营", ["Intel", "AMD"], horizontal=True)
    cpu_list = all_data["cpus"]["Intel_Processors"] if brand == "Intel" else all_data["cpus"]["AMD_Processors"]
    
    selected_cpu_name = st.selectbox("选择 CPU 型号", [c["model"] for c in cpu_list])
    selected_cpu = next(c for c in cpu_list if c["model"] == selected_cpu_name)
    
    c_p = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
    summary_price += c_p
    st.info(f"**接口**: {selected_cpu['socket']} | **规格**: {selected_cpu['specs']}")
    st.sidebar.write(f"CPU: {selected_cpu_name} (￥{c_p})")

    # 2. 主板选择 (根据接口过滤)
    st.header("2. 主板 (Motherboard)")
    # 筛选兼容系列
    comp_series = [s["series"] for s in all_data["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
    # 筛选兼容型号
    comp_boards = [b for b in all_data["m_models"]["motherboard_models"] if b["series"] in comp_series]
    
    if not comp_boards:
        st.warning(f"目前暂无支持 {selected_cpu['socket']} 的主板数据")
        selected_board = None
    else:
        b_choice = st.selectbox("选择兼容主板", [f"{b['brand']} {b['model']}" for b in comp_boards])
        selected_board = next(b for b in comp_boards if f"{b['brand']} {b['model']}" == b_choice)
        
        # 显示 Tagger 生成的标签
        tags = selected_board.get("tags", [])
        st.markdown(" ".join([f"`{t}`" for t in tags]))
        summary_price += selected_board["price"]
        st.sidebar.write(f"主板: {selected_board['model']} (￥{selected_board['price']})")

    # 3. 内存选择 (根据主板标签自动选 DDR4/DDR5)
    st.header("3. 内存 (Memory)")
    if selected_board:
        # 兼容性逻辑：优先看主板标签是否有 DDR4
        req_type = "DDR4" if "DDR4" in selected_board.get("tags", []) else "DDR5"
        
        # 从处理后的内存池中筛选
        mem_items = [m for m in all_data["memory_pool"].values() if m.get("type") == req_type]
        
        if not mem_items:
            st.warning(f"缺少 {req_type} 内存数据")
        else:
            m_choice = st.selectbox(f"选择 {req_type} 内存", [m["display_name"] for m in mem_items])
            selected_mem = next(m for m in mem_items if m["display_name"] == m_choice)
            summary_price += selected_mem["price"]
            st.write(f"频率: {selected_mem['frequency']}MHz | 容量: {selected_mem['capacity']}G")
            st.sidebar.write(f"内存: {selected_mem['display_name']} (￥{selected_mem['price']})")

    # 4. 存储选择
    st.header("4. 存储 (Storage)")
    storages = all_data["storage"]["storage_devices"]
    s_choice = st.selectbox("选择硬盘", [s["display_name"] for s in storages])
    selected_s = next(s for s in storages if s["display_name"] == s_choice)
    summary_price += selected_s["price"]
    st.sidebar.write(f"硬盘: {selected_s['display_name']} (￥{selected_s['price']})")

    # 总计
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"总预算: :red[￥{summary_price}]")
