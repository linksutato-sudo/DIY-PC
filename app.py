import streamlit as st
import json
import os

# --- 集成并改进打标签逻辑 ---
def add_tags_to_motherboards(data):
    if not data or "motherboard_models" not in data:
        return
    for board in data["motherboard_models"]:
        model = board.get("model", "").upper()
        series = board.get("series", "").upper()
        tags = set()
        
        # 识别 DDR 类型：优先看型号，再看系列
        if any(k in model for k in ["D4", "DDR4"]):
            tags.add("DDR4")
        elif any(k in model for k in ["D5", "DDR5"]):
            tags.add("DDR5")
        elif any(c in series for c in ["B760", "Z790", "X870", "Z890", "A620", "B650"]):
            tags.add("DDR5")
        else:
            tags.add("DDR4") # 默认兜底老平台
            
        board["tags"] = list(tags)

# --- 数据加载 ---
@st.cache_data
def get_db():
    def load(fn):
        p = fn if os.path.exists(fn) else os.path.join("data", fn)
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    raw_mem = load("memory_modules.json")
    mem_dict = {}
    if raw_mem and "memory_modules" in raw_mem:
        # 关键剥壳：处理那个万恶的列表嵌套
        content = raw_mem["memory_modules"]
        mem_dict = content[0] if isinstance(content, list) and content else content

    m_models = load("motherboard_models.json")
    if m_models: add_tags_to_motherboards(m_models)

    return {
        "cpus": load("cpus.json"),
        "m_series": load("motherboards_series.json"),
        "m_models": m_models,
        "memory": mem_dict,
        "storage": load("storage_devices.json")
    }

db = get_db()

# --- 界面展示 ---
st.title("🖥️ DIY-PC 智能匹配系统")

# 1. CPU 选择 (省略部分重复逻辑，确保 socket 拿到)
cpu_brand = st.radio("平台", ["Intel", "AMD"], horizontal=True)
cpu_key = "Intel_Processors" if cpu_brand == "Intel" else "AMD_Processors"
cpus = db["cpus"].get(cpu_key, [])
sel_cpu_name = st.selectbox("选择 CPU", [c["model"] for c in cpus])
sel_cpu = next(c for c in cpus if c["model"] == sel_cpu_name)

# 2. 主板选择
v_series = [s["series"] for s in db["m_series"]["Motherboard_Series"] if s["socket"] == sel_cpu["socket"]]
v_boards = [b for b in db["m_models"]["motherboard_models"] if b["series"] in v_series]
if v_boards:
    b_names = [f"{b['brand']} {b['model']}" for b in v_boards]
    sel_b_name = st.selectbox("选择主板", b_names)
    sel_board = next(b for b in v_boards if f"{b['brand']} {b['model']}" == sel_b_name)
else:
    sel_board = None

# --- 重点修复：内存匹配 ---
st.header("3. 内存选择")
if sel_board:
    # 确定目标类型
    target = "DDR4" if "DDR4" in sel_board.get("tags", []) else "DDR5"
    
    # 增加容错：如果 db["memory"] 是列表，强转字典
    m_pool = db["memory"]
    if isinstance(m_pool, list): m_pool = m_pool[0]
    
    # 筛选
    compat_mem = [m for m in m_pool.values() if isinstance(m, dict) and m.get("type") == target]
    
    if compat_mem:
        m_name = st.selectbox(f"匹配的 {target} 内存", [m["display_name"] for m in compat_mem])
        # 使用 display_name 匹配，防止 ID 找不到
        sel_mem = next(m for m in compat_mem if m["display_name"] == m_name)
        st.success(f"已选择: {sel_mem['display_name']} - ￥{sel_mem['price']}")
    else:
        st.error(f"库中没有找到 {target} 类型的内存，请检查 json 里的 type 字段。")

# --- 重点修复：硬盘匹配 ---
st.header("4. 硬盘选择")
if db["storage"] and "storage_devices" in db["storage"]:
    s_list = db["storage"]["storage_devices"]
    if s_list:
        s_names = [s.get("display_name
