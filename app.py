import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# --- 页面设置 ---
st.set_page_config(page_title="DIY-PC 智能装机助手", page_icon="🖥️", layout="wide")

# --- 兼容性路径加载函数 ---
def load_json(filename):
    # 尝试两个路径：直接读取 或 在 data 文件夹下读取
    paths = [filename, os.path.join("data", filename)]
    for path in paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None

@st.cache_data
def get_all_data():
    data = {
        "cpus": load_json("cpus.json"),
        "m_series": load_json("motherboards_series.json"),
        "m_models": load_json("motherboard_models.json"),
        "memory": load_json("memory_modules.json"),
        "storage": load_json("storage_devices.json")
    }
    # 检查必要文件
    if not data["cpus"] or not data["m_models"]:
        st.error("缺少核心数据文件 (cpus.json 或 motherboard_models.json)，请检查文件路径！")
        return None
    
    # 自动打标签
    add_tags_to_motherboards(data["m_models"])
    return data

data = get_all_data()

# --- 主逻辑 ---
st.title("🖥️ DIY-PC 智能硬件导购系统")

if data:
    # 侧边栏：预算汇总
    st.sidebar.header("🛒 已选配置清单")
    total_price = 0

    # 1. CPU 选择
    st.header("1. 选择处理器 (CPU)")
    c1, c2 = st.columns([1, 2])
    with c1:
        brand = st.radio("平台", ["Intel", "AMD"], horizontal=True)
        cpu_list = data["cpus"]["Intel_Processors"] if brand == "Intel" else data["cpus"]["AMD_Processors"]
        cpu_model = st.selectbox("型号", [c["model"] for c in cpu_list])
    
    selected_cpu = next(c for c in cpu_list if c["model"] == cpu_model)
    cpu_p = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price") or 0
    total_price += cpu_p
    
    with c2:
        st.info(f"**插槽**: {selected_cpu['socket']} | **规格**: {selected_cpu['specs']}")
        st.metric("价格", f"￥{cpu_p}")

    # 2. 主板选择 (根据接口过滤)
    st.header("2. 选择主板")
    # 找出支持该接口的系列
    valid_series = [s["series"] for s in data["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
    # 找出属于这些系列的模型
    compat_boards = [b for b in data["m_models"]["motherboard_models"] if b["series"] in valid_series]

    if not compat_boards:
        st.warning(f"⚠️ 暂无兼容 {selected_cpu['socket']} 接口的主板数据")
        selected_board = None
    else:
        b1, b2 = st.columns([1, 2])
        with b1:
            board_choice = st.selectbox("兼容主板列表", [f"{b['brand']} {b['model']}" for b in compat_boards])
            selected_board = next(b for b in compat_boards if f"{b['brand']} {b['model']}" == board_choice)
        with b2:
            tags = selected_board.get("tags", [])
            st.write(" ".join([f"`{t}`" for t in tags]))
            st.metric("价格", f"￥{selected_board['price']}")
            total_price += selected_board['price']

    # 3. 内存选择 (根据主板标签判断 DDR4/DDR5)
    st.header("3. 选择内存")
    if selected_board:
        # 判断是 DDR4 还是 DDR5
        is_d4 = "DDR4" in selected_board.get("tags", [])
        target_type = "DDR4" if is_d4 else "DDR5"
        
        # 兼容你的 JSON 结构（处理 memory_modules 可能在列表中的情况）
        mem_source = data["memory"]["memory_modules"]
        if isinstance(mem_source, list): mem_source = mem_source[0]
        
        compat_mem = [m for m in mem_source.values() if m["type"] == target_type]
        
        m1, m2 = st.columns([1, 2])
        with m1:
            mem_choice = st.selectbox(f"匹配的 {target_type} 内存", [m["display_name"] for m in compat_mem])
            selected_mem = next(m for m in compat_mem if m["display_name"] == mem_choice)
        with m2:
            st.write(f"**频率**: {selected_mem['frequency']}MHz | **容量**: {selected_mem['capacity']}G")
            st.metric("价格", f"￥{selected_mem['price']}")
            total_price += selected_mem['price']

    # 4. 硬盘选择
    st.header("4. 选择硬盘")
    storage_list = data["storage"]["storage_devices"]
    s1, s2 = st.columns([1, 2])
    with s1:
        st_choice = st.selectbox("固态硬盘", [s["display_name"] for s in storage_list])
        selected_st = next(s for s in storage_list if s["display_name"] == st_choice)
    with s2:
        st.write(f"**容量**: {selected_st['capacity']}GB | **级别**: {selected_st.get('level', 'N/A')}")
        st.metric("价格", f"￥{selected_st['price']}")
        total_price += selected_st['price']

    # 侧边栏总结
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"总计金额: :red[￥{total_price}]")
    st.sidebar.write(f"1. CPU: {selected_cpu['model']}")
    if selected_board: st.sidebar.write(f"2. 主板: {selected_board['model']}")
    st.sidebar.write(f"3. 内存: {selected_mem['display_name']}")
    st.sidebar.write(f"4. 硬盘: {selected_st['display_name']}")
