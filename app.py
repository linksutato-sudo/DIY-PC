import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 页面设置 ---
st.set_page_config(page_title="DIY-PC 智能导购", layout="wide")

# --- 1. 强力加载逻辑 ---
def safe_load(file_name):
    # 同时兼容当前目录和 data 目录
    paths = [file_name, os.path.join("data", file_name)]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_hardware_db():
    raw_cpus = safe_load("cpus.json")
    raw_series = safe_load("motherboards_series.json")
    raw_models = safe_load("motherboard_models.json")
    raw_mem = safe_load("memory_modules.json")
    raw_storage = safe_load("storage_devices.json")

    # --- 关键：内存库剥壳逻辑 ---
    # 你的 JSON 是 {"memory_modules": [ { "id": {...} } ]}
    mem_dict = {}
    if raw_mem and "memory_modules" in raw_mem:
        inner = raw_mem["memory_modules"]
        # 如果是列表 [ {...} ]，取第 0 个元素变成字典 {...}
        if isinstance(inner, list) and len(inner) > 0:
            mem_dict = inner[0]
        elif isinstance(inner, dict):
            mem_dict = inner

    # 给主板打标签
    if raw_models:
        add_tags_to_motherboards(raw_models)

    return {
        "cpus": raw_cpus,
        "series": raw_series,
        "models": raw_models,
        "memory": mem_dict,  # 此时这里已经是纯字典了
        "storage": raw_storage
    }

db = get_hardware_db()

# --- 2. 界面逻辑 ---
st.title("🖥️ DIY-PC 硬件导购助手")

if not db["cpus"]:
    st.error("数据加载失败，请检查 .json 文件位置！")
    st.stop()

# 侧边栏汇总
st.sidebar.header("🛒 配置清单")
total_sum = 0

# Step 1: CPU
st.header("1. 处理器 (CPU)")
c_platform = st.radio("平台", ["Intel", "AMD"], horizontal=True)
c_key = "Intel_Processors" if c_platform == "Intel" else "AMD_Processors"
cpu_list = db["cpus"].get(c_key, [])
sel_cpu_name = st.selectbox("型号", [c["model"] for c in cpu_list])
sel_cpu = next(c for c in cpu_list if c["model"] == sel_cpu_name)

c_p = sel_cpu.get("tray_price") or sel_cpu.get("boxed_price") or 0
total_sum += c_p
st.info(f"**插槽**: {sel_cpu['socket']} | **价格**: ￥{c_p}")
st.sidebar.write(f"CPU: {sel_cpu_name}")

# Step 2: 主板
st.header("2. 主板 (Motherboard)")
# 匹配 Socket
v_series = [s["series"] for s in db["series"]["Motherboard_Series"] if s["socket"] == sel_cpu["socket"]]
v_boards = [b for b in db["models"]["motherboard_models"] if b["series"] in v_series]

if not v_boards:
    st.warning("无匹配主板")
    sel_board = None
else:
    b_name = st.selectbox("兼容主板", [f"{b['brand']} {b['model']}" for b in v_boards])
    sel_board = next(b for b in v_boards if f"{b['brand']} {b['model']}" == b_name)
    st.write(" ".join([f"`{t}`" for t in sel_board.get("tags", [])]))
    total_sum += sel_board["price"]
    st.sidebar.write(f"主板: {sel_board['model']}")

# Step 3: 内存 (此时 db["memory"] 是字典，可以用 .values())
st.header("3. 内存 (Memory)")
if sel_board:
    # 自动识别主板需要的 DDR 类型
    req_type = "DDR4" if "DDR4" in sel_board.get("tags", []) else "DDR5"
    
    # 在字典 values 中筛选
    mem_items = [m for m in db["memory"].values() if isinstance(m, dict) and m.get("type") == req_type]
    
    if mem_items:
        m_name = st.selectbox(f"匹配的 {req_type} 内存", [m["display_name"] for m in mem_items])
        sel_mem = next(m for m in mem_items if m["display_name"] == m_name)
        st.write(f"规格: {sel_mem['frequency']}MHz | 价格: ￥{sel_mem['price']}")
        total_sum += sel_mem["price"]
        st.sidebar.write(f"内存: {sel_mem['display_name']}")
    else:
        st.warning(f"库中暂无 {req_type} 内存数据")

# Step 4: 硬盘
st.header("4. 硬盘 (Storage)")
storages = db["storage"]["storage_devices"]
s_name = st.selectbox("固态硬盘", [s["display_name"] for s in storages])
sel_s = next(s for s in storages if s["display_name"] == s_name)
total_sum += sel_s["price"]
st.sidebar.write(f"硬盘: {sel_s['display_name']}")

st.sidebar.markdown("---")
st.sidebar.subheader(f"总预算: :red[￥{total_sum}]")
