import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 1. 基础配置 ---
st.set_page_config(page_title="DIY-PC 智能装机", layout="wide")

# --- 2. 强力数据加载函数 ---
def load_json(file_name):
    # 兼容本地和 data 目录
    paths = [file_name, os.path.join("data", file_name)]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_db():
    # 读取原始数据
    cpus = load_json("cpus.json")
    m_series = load_json("motherboards_series.json")
    m_models = load_json("motherboard_models.json")
    mem_raw = load_json("memory_modules.json")
    storage = load_json("storage_devices.json")

    # --- 内存数据“深度剥壳” ---
    final_memory_dict = {}
    if mem_raw and "memory_modules" in mem_raw:
        content = mem_raw["memory_modules"]
        # 情况 A: 结构是 [{"id":{...}}] -> 剥开列表取 [0]
        if isinstance(content, list) and len(content) > 0:
            final_memory_dict = content[0]
        # 情况 B: 结构直接是 {"id":{...}}
        elif isinstance(content, dict):
            final_memory_dict = content
            
    # 主板自动打标签 (用于识别 DDR4/DDR5)
    if m_models:
        add_tags_to_motherboards(m_models)

    return {
        "cpus": cpus,
        "m_series": m_series,
        "m_models": m_models,
        "memory": final_memory_dict, # 确保这里是一个纯字典
        "storage": storage
    }

# 初始化数据库
db = get_db()

# --- 3. 页面展示逻辑 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not db["cpus"]:
    st.error("❌ 未能读取到 cpus.json，请检查文件路径！")
    st.stop()

# 侧边栏：配置单汇总
st.sidebar.title("🛒 配置清单")
total_sum = 0

# --- 1. CPU 选择 ---
st.header("1. 处理器 (CPU)")
platform = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
cpu_key = "Intel_Processors" if platform == "Intel" else "AMD_Processors"
cpu_list = db["cpus"].get(cpu_key, [])

sel_cpu_name = st.selectbox("选择型号", [c["model"] for c in cpu_list])
sel_cpu = next(c for c in cpu_list if c["model"] == sel_cpu_name)

cpu_p = sel_cpu.get("tray_price") or sel_cpu.get("boxed_price") or 0
total_sum += cpu_p
st.info(f"**接口**: {sel_cpu['socket']} | **规格**: {sel_cpu['specs']}")
st.sidebar.write(f"CPU: {sel_cpu_name} (￥{cpu_p})")

# --- 2. 主板选择 ---
st.header("2. 主板 (Motherboard)")
# 匹配插槽 (Socket)
valid_series = [s["series"] for s in db["m_series"]["Motherboard_Series"] if s["socket"] == sel_cpu["socket"]]
valid_boards = [b for b in db["m_models"]["motherboard_models"] if b["series"] in valid_series]

if not valid_boards:
    st.warning("暂无匹配主板数据")
    sel_board = None
else:
    b_name = st.selectbox("选择兼容主板", [f"{b['brand']} {b['model']}" for b in valid_boards])
    sel_board = next(b for b in valid_boards if f"{b['brand']} {b['model']}" == b_name)
    # 显示标签
    st.write(" ".join([f"`{t}`" for t in sel_board.get("tags", [])]))
    total_sum += sel_board["price"]
    st.sidebar.write(f"主板: {sel_board['model']} (￥{sel_board['price']})")

# --- 3. 内存选择 (这里是之前报错的重灾区) ---
st.header("3. 内存 (Memory)")
if sel_board:
    # 自动识别主板标签
    target_type = "DDR4" if "DDR4" in sel_board.get("tags", []) else "DDR5"
    
    # 核心保护：确保 db["memory"] 是字典后才调用 .values()
    mem_pool = db["memory"]
    if isinstance(mem_pool, dict):
        # 筛选对应类型的内存
        compat_mem = [m for m in mem_pool.values() if isinstance(m, dict) and m.get("type") == target_type]
        
        if compat_mem:
            m_choice = st.selectbox(f"匹配的 {target_type} 内存", [m["display_name"] for m in compat_mem])
            sel_mem = next(m for m in compat_mem if m["display_name"] == m_choice)
            st.write(f"频率: {sel_mem['frequency']}MHz | 价格: ￥{sel_mem['price']}")
            total_sum += sel_mem["price"]
            st.sidebar.write(f"内存: {sel_mem['display_name']} (￥{sel_mem['price']})")
        else:
            st.warning(f"内存库中暂无 {target_type} 型号")
    else:
        st.error("内存数据格式异常，无法解析字典")

# --- 4. 硬盘选择 ---
st.header("4. 硬盘 (Storage)")
s_list = db["storage"]["storage_devices"]
s_choice = st.selectbox("选择固态硬盘", [s["display_name"] for s in s_list])
sel_s = next(s for s in s_list if s["display_name"] == s_choice)
total_sum += sel_s["price"]
st.sidebar.write(f"硬盘: {sel_s['display_name']} (￥{sel_s['price']})")

# --- 总结 ---
st.sidebar.markdown("---")
st.sidebar.subheader(f"总计金额: :red[￥{total_sum}]")
