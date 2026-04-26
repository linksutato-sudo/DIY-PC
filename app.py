import streamlit as st
import json
import os

# --- 1. 原 tagger.py 逻辑集成 ---
def add_tags_to_motherboards(data):
    """直接在内部给主板数据打标签，省去外部引用"""
    DDR4_KEYWORDS = ["D4", "DDR4"]
    DDR5_CHIPSETS = ["Z790", "Z890", "X870", "B850", "B760"]
    
    if "motherboard_models" not in data:
        return

    for board in data["motherboard_models"]:
        model = board["model"].upper()
        series = board["series"].upper()
        tags = set()

        # WIFI 识别
        if "WIFI" in model or "WIRELESS" in model:
            tags.add("WIFI")
        
        # DDR4 / DDR5 识别 (核心：决定了后面内存的过滤)
        if any(k in model for k in DDR4_KEYWORDS):
            tags.add("DDR4")
        elif any(c in series for c in DDR5_CHIPSETS):
            tags.add("DDR5")
        else:
            # 默认兜底策略：如果是老插槽(如B450/B550)多为DDR4，新插槽多为DDR5
            if any(s in series for s in ["B450", "B550", "X570", "A520"]):
                tags.add("DDR4")
            else:
                tags.add("DDR5")

        board["tags"] = list(tags)

# --- 2. 页面与数据加载 ---
st.set_page_config(page_title="DIY-PC 智能助手", layout="wide")

def load_json(file_name):
    # 兼容云端路径逻辑
    paths = [file_name, os.path.join("data", file_name), os.path.join("/mount/src/diy-pc/", file_name)]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_hardware_db():
    raw_cpus = load_json("cpus.json")
    raw_series = load_json("motherboards_series.json")
    raw_models = load_json("motherboard_models.json")
    raw_mem = load_json("memory_modules.json")
    raw_storage = load_json("storage_devices.json")

    # 内存剥壳：解决 [{"id":{...}}] 结构
    mem_dict = {}
    if raw_mem and "memory_modules" in raw_mem:
        content = raw_mem["memory_modules"]
        if isinstance(content, list) and len(content) > 0:
            mem_dict = content[0]
        elif isinstance(content, dict):
            mem_dict = content

    # 调用内置标签函数
    if raw_models:
        add_tags_to_motherboards(raw_models)

    return {
        "cpus": raw_cpus,
        "series": raw_series,
        "models": raw_models,
        "memory": mem_dict,
        "storage": raw_storage
    }

db = get_hardware_db()

# --- 3. UI 界面 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not db["cpus"]:
    st.error("数据加载失败。请确保 JSON 文件在项目根目录或 data/ 目录下。")
    st.stop()

st.sidebar.title("🛒 我的配置单")
total = 0

# Step 1: CPU
st.header("1. 处理器")
brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
cpu_key = "Intel_Processors" if brand == "Intel" else "AMD_Processors"
cpus = db["cpus"].get(cpu_key, [])
sel_cpu_name = st.selectbox("选择 CPU", [c["model"] for c in cpus])
sel_cpu = next(c for c in cpus if c["model"] == sel_cpu_name)
c_p = sel_cpu.get("tray_price") or sel_cpu.get("boxed_price") or 0
total += c_p
st.info(f"针脚: {sel_cpu['socket']} | 规格: {sel_cpu['specs']}")

# Step 2: 主板
st.header("2. 主板")
v_series = [s["series"] for s in db["series"]["Motherboard_Series"] if s["socket"] == sel_cpu["socket"]]
v_boards = [b for b in db["models"]["motherboard_models"] if b["series"] in v_series]

if not v_boards:
    st.warning("未找到匹配主板")
    sel_board = None
else:
    b_name = st.selectbox("选择主板", [f"{b['brand']} {b['model']}" for b in v_boards])
    sel_board = next(b for b in v_boards if f"{b['brand']} {b['model']}" == b_name)
    st.write(" ".join([f"`{t}`" for t in sel_board.get("tags", [])]))
    total += sel_board["price"]

# Step 3: 内存
st.header("3. 内存")
if sel_board:
    target = "DDR4" if "DDR4" in sel_board.get("tags", []) else "DDR5"
    # 只要 db["memory"] 是剥壳后的字典，values() 就一定能跑通
    mem_opts = [m for m in db["memory"].values() if isinstance(m, dict) and m.get("type") == target]
    
    if mem_opts:
        m_name = st.selectbox(f"匹配的 {target} 内存", [m["display_name"] for m in mem_opts])
        sel_mem = next(m for m in mem_opts if m["display_name"] == m_name)
        st.write(f"规格: {sel_mem['frequency']}MHz | 价格: ￥{sel_mem['price']}")
        total += sel_mem["price"]
    else:
        st.warning(f"缺少 {target} 内存数据")

# Step 4: 硬盘
st.header("4. 硬盘")
storages = db["storage"]["storage_devices"]
s_name = st.selectbox("选择固态硬盘", [s["display_name"] for s in storages])
sel_s = next(s for s in storages if s["display_name"] == s_name)
total += sel_s["price"]

# 侧边栏总结
st.sidebar.write(f"**CPU**: {sel_cpu_name}")
if sel_board: st.sidebar.write(f"**主板**: {sel_board['model']}")
st.sidebar.write(f"**硬盘**: {sel_s['display_name']}")
st.sidebar.markdown("---")
st.sidebar.subheader(f"总计: :red[￥{total}]")
