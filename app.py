import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 1. 页面配置 ---
st.set_page_config(page_title="DIY-PC 智能装机助手", page_icon="🖥️", layout="wide")

# --- 2. 核心数据加载（带防御逻辑） ---
def load_json(file_name):
    # 尝试多个可能的路径
    paths = [file_name, os.path.join("data", file_name)]
    for path in paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_hardware_data():
    raw = {
        "cpus": load_json("cpus.json"),
        "m_series": load_json("motherboards_series.json"),
        "m_models": load_json("motherboard_models.json"),
        "memory": load_json("memory_modules.json"),
        "storage": load_json("storage_devices.json")
    }

    # --- 内存数据精准剥壳 ---
    # 结构：{"memory_modules": [ { "id": {...} } ]}
    processed_memory = {}
    if raw["memory"] and "memory_modules" in raw["memory"]:
        mem_list = raw["memory"]["memory_modules"]
        if isinstance(mem_list, list) and len(mem_list) > 0:
            processed_memory = mem_list[0]  # 核心：取列表第一项得到字典
    raw["cleaned_memory"] = processed_memory

    # 运行 tagger 给主板打标签（DDR4/DDR5/WIFI等）
    if raw["m_models"]:
        add_tags_to_motherboards(raw["m_models"])
    
    return raw

data = get_hardware_data()

# --- 3. 界面逻辑 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if not data["cpus"] or not data["m_models"]:
    st.error("❌ 基础数据加载失败，请检查 JSON 文件位置。")
    st.stop()

# 初始化侧边栏和总价
st.sidebar.title("🛒 我的配置清单")
total_price = 0

# --- 第一步：CPU 选择 ---
st.header("1. 选择处理器 (CPU)")
col_cpu1, col_cpu2 = st.columns([1, 2])
with col_cpu1:
    platform = st.radio("平台选择", ["Intel", "AMD"], horizontal=True)
    cpu_list = data["cpus"]["Intel_Processors"] if platform == "Intel" else data["cpus"]["AMD_Processors"]
    cpu_names = [c["model"] for c in cpu_list]
    selected_cpu_name = st.selectbox("搜索 CPU 型号", cpu_names)
    selected_cpu = next(c for c in cpu_list if c["model"] == selected_cpu_name)

with col_cpu2:
    cpu_price = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
    st.info(f"**插槽**: {selected_cpu['socket']} | **规格**: {selected_cpu['specs']}")
    st.metric("CPU 价格", f"￥{cpu_price}")
    total_price += cpu_price
    st.sidebar.write(f"**CPU**: {selected_cpu_name} (￥{cpu_price})")

# --- 第二步：主板选择（基于插槽兼容） ---
st.header("2. 选择主板 (Motherboard)")
# 过滤兼容的系列
compat_series = [s["series"] for s in data["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
# 过滤兼容的型号
compat_boards = [b for b in data["m_models"]["motherboard_models"] if b["series"] in compat_series]

if not compat_boards:
    st.warning(f"⚠️ 暂无兼容 {selected_cpu['socket']} 接口的主板数据")
    selected_board = None
else:
    col_mb1, col_mb2 = st.columns([1, 2])
    with col_mb1:
        board_names = [f"{b['brand']} {b['model']}" for b in compat_boards]
        selected_board_full = st.selectbox("选择兼容主板", board_names)
        selected_board = next(b for b in compat_boards if f"{b['brand']} {b['model']}" == selected_board_full)
    
    with col_mb2:
        tags = selected_board.get("tags", [])
        tag_html = "".join([f'<span style="background-color:#007bff; color:white; padding:2px 8px; border-radius:10px; margin-right:5px; font-size:12px;">{t}</span>' for t in tags])
        st.markdown(tag_html, unsafe_allow_html=True)
        st.metric("主板价格", f"￥{selected_board['price']}")
        total_price += selected_board["price"]
        st.sidebar.write(f"**主板**: {selected_board['model']} (￥{selected_board['price']})")

# --- 第三步：内存选择（基于主板 DDR 类型） ---
st.header("3. 选择内存 (Memory)")
if selected_board:
    # 自动识别内存需求：如果主板标签里有 DDR4，则过滤 DDR4 内存，否则默认 DDR5
    target_type = "DDR4" if "DDR4" in selected_board.get("tags", []) else "DDR5"
    
    # 从清洗后的内存池中筛选
    mem_pool = data["cleaned_memory"]
    compat_mem = [m for m in mem_pool.values() if isinstance(m, dict) and m.get("type") == target_type]
    
    if not compat_mem:
        st.warning(f"💡 内存库中暂无匹配的 {target_type} 型号")
    else:
        col_m1, col_m2 = st.columns([1, 2])
        with col_m1:
            m_names = [m["display_name"] for m in compat_mem]
            selected_m_name = st.selectbox(f"匹配的 {target_type} 内存", m_names)
            selected_mem = next(m for m in compat_mem if m["display_name"] == selected_m_name)
        
        with col_m2:
            st.write(f"**频率**: {selected_mem['frequency']}MHz | **容量**: {selected_mem['capacity']}G")
            st.metric("内存价格", f"￥{selected_mem['price']}")
            total_price += selected_mem["price"]
            st.sidebar.write(f"**内存**: {selected_mem['display_name']} (￥{selected_mem['price']})")
else:
    st.write("请先选择主板以匹配内存类型。")

# --- 第四步：硬盘选择 ---
st.header("4. 选择硬盘 (Storage)")
storage_list = data["storage"]["storage_devices"]
col_s1, col_s2 = st.columns([1, 2])
with col_s1:
    s_names = [s["display_name"] for s in storage_list]
    selected_s_name = st.selectbox("选择固态硬盘", s_names)
    selected_storage = next(s for s in storage_list if s["display_name"] == selected_s_name)

with col_s2:
    st.write(f"**类型**: {selected_storage['type']} | **容量**: {selected_storage['capacity']}GB")
    st.metric("硬盘价格", f"￥{selected_storage['price']}")
    total_price += selected_storage["price"]
    st.sidebar.write(f"**硬盘**: {selected_storage['display_name']} (￥{selected_storage['price']})")

# --- 总结结算 ---
st.sidebar.markdown("---")
st.sidebar.subheader(f"总计金额: :red[￥{total_price}]")
if st.sidebar.button("导出配置单", use_container_width=True):
    st.sidebar.success("配置单已保存！(演示)")
