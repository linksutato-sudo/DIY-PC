import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️", layout="wide")

# --- 强力加载函数 ---
def load_json_safely(filename):
    paths = [filename, os.path.join("data", filename)]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
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

    # --- 核心修复：内存数据提取逻辑 ---
    mem_pool = {}
    raw_mem = data.get("memory")
    if raw_mem:
        # 情况 A: 结构是 {"memory_modules": [{...}]}
        if isinstance(raw_mem, dict) and "memory_modules" in raw_mem:
            inner = raw_mem["memory_modules"]
            mem_pool = inner[0] if isinstance(inner, list) else inner
        # 情况 B: 结构是 [{...}] (直接是列表)
        elif isinstance(raw_mem, list):
            mem_pool = raw_mem[0]
        # 情况 C: 直接就是数据字典
        else:
            mem_pool = raw_mem
    
    data["cleaned_memory"] = mem_pool

    # 运行打标签逻辑
    if data["m_models"]:
        add_tags_to_motherboards(data["m_models"])
    
    return data

hardware = get_all_hardware()

# --- 界面展示 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not hardware["cpus"]:
    st.error("无法找到数据文件，请检查文件是否在当前目录或 data 文件夹下。")
    st.stop()

total_price = 0

# 1. CPU
st.header("1. 处理器")
brand = st.radio("平台", ["Intel", "AMD"], horizontal=True)
cpu_list = hardware["cpus"]["Intel_Processors"] if brand == "Intel" else hardware["cpus"]["AMD_Processors"]
cpu_name = st.selectbox("选择型号", [c["model"] for c in cpu_list])
selected_cpu = next(c for c in cpu_list if c["model"] == cpu_name)
cpu_p = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
st.info(f"针脚: {selected_cpu['socket']} | 规格: {selected_cpu['specs']}")
total_price += cpu_p

# 2. 主板 (基于 Socket 过滤)
st.header("2. 主板")
valid_series = [s["series"] for s in hardware["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
compat_boards = [b for b in hardware["m_models"]["motherboard_models"] if b["series"] in valid_series]

if not compat_boards:
    st.warning("暂无匹配的主板")
    selected_board = None
else:
    b_name = st.selectbox("选择主板", [f"{b['brand']} {b['model']}" for b in compat_boards])
    selected_board = next(b for b in compat_boards if f"{b['brand']} {b['model']}" == b_name)
    st.write(" ".join([f"`{t}`" for t in selected_board.get("tags", [])]))
    total_price += selected_board["price"]

# 3. 内存 (自动匹配 DDR4/DDR5)
st.header("3. 内存")
if selected_board:
    # 只要主板型号里有 D4/DDR4 或者是 H610/B760 等特定型号，tagger 就会打上 DDR4 标签
    is_d4 = "DDR4" in selected_board.get("tags", [])
    target_type = "DDR4" if is_d4 else "DDR5"
    
    # 从我们清洗后的 cleaned_memory 中选
    mem_items = [m for m in hardware["cleaned_memory"].values() if isinstance(m, dict) and m.get("type") == target_type]
    
    if mem_items:
        m_name = st.selectbox(f"匹配的 {target_type} 内存", [m["display_name"] for m in mem_items])
        selected_mem = next(m for m in mem_items if m["display_name"] == m_name)
        st.write(f"规格: {selected_mem['frequency']}MHz | 价格: ￥{selected_mem['price']}")
        total_price += selected_mem["price"]
    else:
        st.warning(f"内存库中没有找到对应的 {target_type} 型号")

# 总结
st.sidebar.title("💰 预算统计")
st.sidebar.metric("总计金额", f"￥{total_price}")
st.sidebar.write(f"CPU: {cpu_name}")
if selected_board: st.sidebar.write(f"主板: {selected_board['model']}")
