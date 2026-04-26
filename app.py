import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 页面配置 ---
st.set_page_config(page_title="PC DIY 助手", layout="wide")

# --- 1. 强力数据加载 ---
def load_data(file_name):
    # 自动搜索当前目录和 data 目录
    paths = [file_name, os.path.join("data", file_name)]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_all_data():
    raw_cpus = load_data("cpus.json")
    raw_m_series = load_data("motherboards_series.json")
    raw_m_models = load_data("motherboard_models.json")
    raw_mem = load_data("memory_modules.json")
    raw_storage = load_data("storage_devices.json")

    # --- 内存剥壳核心逻辑 ---
    # 目标：把 [{"id":{...}}] 变成 {"id":{...}}
    mem_dict = {}
    if raw_mem and "memory_modules" in raw_mem:
        content = raw_mem["memory_modules"]
        if isinstance(content, list) and len(content) > 0:
            mem_dict = content[0] # 穿透列表，拿到真正的字典
        elif isinstance(content, dict):
            mem_dict = content
            
    # 主板打标签
    if raw_m_models:
        add_tags_to_motherboards(raw_m_models)

    return {
        "cpus": raw_cpus,
        "m_series": raw_m_series,
        "m_models": raw_m_models,
        "memory": mem_dict,  # 这里存的是已经剥壳的字典
        "storage": raw_storage
    }

db = get_all_data()

# --- 2. 界面展示 ---
st.title("🖥️ PC DIY 智能装机助手")

if not db["cpus"]:
    st.error("数据加载失败，请检查 JSON 文件是否存在。")
    st.stop()

# 侧边栏：配置单
st.sidebar.title("🛒 配置清单")
total = 0

# --- 步骤 1: CPU ---
st.header("1. 处理器")
brand = st.radio("品牌", ["Intel", "AMD"], horizontal=True)
cpu_key = "Intel_Processors" if brand == "Intel" else "AMD_Processors"
cpus = db["cpus"].get(cpu_key, [])
sel_cpu_name = st.selectbox("选择 CPU", [c["model"] for c in cpus])
sel_cpu = next(c for c in cpus if c["model"] == sel_cpu_name)

price_c = sel_cpu.get("tray_price") or sel_cpu.get("boxed_price") or 0
total += price_c
st.sidebar.write(f"CPU: {sel_cpu_name} (￥{price_c})")

# --- 步骤 2: 主板 (自动过滤 Socket) ---
st.header("2. 主板")
# 找出兼容插槽的系列
valid_series = [s["series"] for s in db["m_series"]["Motherboard_Series"] if s["socket"] == sel_cpu["socket"]]
# 找出这些系列下的具体型号
valid_boards = [b for b in db["m_models"]["motherboard_models"] if b["series"] in valid_series]

if not valid_boards:
    st.warning("未找到匹配主板")
    sel_board = None
else:
    sel_b_name = st.selectbox("选择主板", [f"{b['brand']} {b['model']}" for b in valid_boards])
    sel_board = next(b for b in valid_boards if f"{b['brand']} {b['model']}" == sel_b_name)
    tags = sel_board.get("tags", [])
    st.write(" ".join([f"`{t}`" for t in tags]))
    total += sel_board["price"]
    st.sidebar.write(f"主板: {sel_board['model']} (￥{sel_board['price']})")

# --- 步骤 3: 内存 (自动匹配 DDR4/DDR5) ---
st.header("3. 内存")
if sel_board:
    # 逻辑：主板型号带 D4/DDR4 就是 DDR4，否则默认 DDR5
    target = "DDR4" if "DDR4" in sel_board.get("tags", []) else "DDR5"
    
    # 因为 db["memory"] 已经是剥过壳的字典了，现在可以放心用 .values()
    mem_options = [m for m in db["memory"].values() if m.get("type") == target]
    
    if mem_options:
        sel_m_name = st.selectbox(f"匹配的 {target} 内存", [m["display_name"] for m in mem_options])
        sel_mem = next(m for m in mem_options if m["display_name"] == sel_m_name)
        st.write(f"频率: {sel_mem['frequency']} | 价格: ￥{sel_mem['price']}")
        total += sel_mem["price"]
        st.sidebar.write(f"内存: {sel_mem['display_name']} (￥{sel_mem['price']})")
    else:
        st.warning(f"库中缺少 {target} 内存数据")

# --- 步骤 4: 硬盘 ---
st.header("4. 硬盘")
storages = db["storage"]["storage_devices"]
sel_s_name = st.selectbox("选择硬盘", [s["display_name"] for s in storages])
sel_s = next(s for s in storages if s["display_name"] == sel_s_name)
total += sel_s["price"]
st.sidebar.write(f"硬盘: {sel_s['display_name']} (￥{sel_s['price']})")

st.sidebar.markdown("---")
st.sidebar.subheader(f"总预算: :red[￥{total}]")
