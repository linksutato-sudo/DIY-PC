import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 页面基础配置 ---
st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️", layout="wide")

# --- 1. 强力加载函数：解决路径和嵌套问题 ---
def load_json_safely(filename):
    paths = [filename, os.path.join("data", filename)]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                continue
    return None

@st.cache_data
def get_all_hardware():
    data = {
        "cpus": load_json_safely("cpus.json"),
        "m_series": load_json_safely("motherboards_series.json"),
        "m_models": load_json_safely("motherboard_models.json"),
        "memory": load_json_safely("memory_modules.json"),
        "storage": load_json_safely("storage_devices.json")
    }

    # --- 核心修复：内存数据“剥壳”逻辑 ---
    # 针对你截图中的结构：{"memory_modules": [ { "id1": {...}, "id2": {...} } ]}
    mem_pool = {}
    raw_mem_data = data.get("memory", {})
    
    if isinstance(raw_mem_data, dict) and "memory_modules" in raw_mem_data:
        # 拿到那个列表 [ {...} ]
        mem_list = raw_mem_data["memory_modules"]
        if isinstance(mem_list, list) and len(mem_list) > 0:
            # 拿到列表里的第一个元素（这才是真正的字典）
            mem_pool = mem_list[0] 
        elif isinstance(mem_list, dict):
            mem_pool = mem_list
    elif isinstance(raw_mem_data, list) and len(raw_mem_data) > 0:
        mem_pool = raw_mem_data[0]
    
    data["cleaned_memory"] = mem_pool

    # 运行打标签逻辑 (tagger.py)
    if data["m_models"]:
        add_tags_to_motherboards(data["m_models"])
    
    return data

hardware = get_all_hardware()

# --- 2. 界面展示逻辑 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not hardware["cpus"]:
    st.error("❌ 无法加载数据，请确保 JSON 文件放在 data 文件夹或程序同级目录下。")
    st.stop()

total_price = 0

# --- 步骤 1: CPU ---
st.header("1. 处理器 (CPU)")
c_brand = st.radio("平台选择", ["Intel", "AMD"], horizontal=True)
c_list = hardware["cpus"].get("Intel_Processors", []) if c_brand == "Intel" else hardware["cpus"].get("AMD_Processors", [])
c_name = st.selectbox("选择型号", [c["model"] for c in c_list])
selected_cpu = next(c for c in c_list if c["model"] == c_name)
c_price = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
total_price += c_price
st.info(f"**接口**: {selected_cpu['socket']} | **规格**: {selected_cpu['specs']}")

# --- 步骤 2: 主板 ---
st.header("2. 主板 (Motherboard)")
m_series_data = hardware["m_series"].get("Motherboard_Series", [])
v_series = [s["series"] for s in m_series_data if s["socket"] == selected_cpu["socket"]]
c_boards = [b for b in hardware["m_models"].get("motherboard_models", []) if b["series"] in v_series]

if not c_boards:
    st.warning(f"⚠️ 未找到支持 {selected_cpu['socket']} 接口的主板")
    selected_board = None
else:
    b_name = st.selectbox("兼容主板列表", [f"{b['brand']} {b['model']}" for b in c_boards])
    selected_board = next(b for b in c_boards if f"{b['brand']} {b['model']}" == b_name)
    tags = selected_board.get("tags", [])
    st.markdown(" ".join([f"`{t}`" for t in tags]))
    total_price += selected_board["price"]

# --- 步骤 3: 内存 (彻底修复 KeyError 和 AttributeError) ---
st.header("3. 内存 (Memory)")
if selected_board:
    # 根据主板标签判断 DDR4/5
    target_type = "DDR4" if "DDR4" in selected_board.get("tags", []) else "DDR5"
    
    # 获取清洗后的内存池字典
    mem_pool = hardware.get("cleaned_memory", {})
    
    # 筛选匹配类型的内存
    # 增加类型检查，确保 m 是字典且包含 'type' 键
    mem_items = []
    if isinstance(mem_pool, dict):
        mem_items = [m for m in mem_pool.values() if isinstance(m, dict) and m.get("type") == target_type]

    if mem_items:
        m_display = st.selectbox(f"匹配的 {target_type} 内存", [m["display_name"] for m in mem_items])
        selected_mem = next(m for m in mem_items if m["display_name"] == m_display)
        st.write(f"规格: {selected_mem['frequency']}MHz | 价格: ￥{selected_mem['price']}")
        total_price += selected_mem["price"]
    else:
        st.warning(f"💡 内存库中暂无匹配的 {target_type} 型号")

# --- 步骤 4: 硬盘 ---
st.header("4. 硬盘 (Storage)")
s_list = hardware["storage"].get("storage_devices", [])
s_display = st.selectbox("选择固态硬盘", [s["display_name"] for s in s_list])
selected_s = next(s for s in s_list if s["display_name"] == s_display)
total_price += selected_s["price"]

# --- 侧边栏总结 ---
st.sidebar.title("🛒 配置总结")
st.sidebar.markdown(f"### 总金额: :red[￥{total_price}]")
st.sidebar.write(f"- CPU: {c_name}")
if selected_board: st.sidebar.write(f"- 主板: {selected_board['model']}")
st.sidebar.write(f"- 硬盘: {selected_s['display_name']}")
