import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# 配置页面
st.set_page_config(page_title="DIY-PC 智能导购专业版", page_icon="🖥️", layout="wide")

# --- 数据加载函数 ---
def load_data():
    base_path = 'data'
    # 确保兼容性：如果文件不在 data 目录下，请根据实际情况修改路径
    files = {
        "cpus": "cpus.json",
        "m_series": "motherboards_series.json",
        "m_models": "motherboard_models.json",
        "memory": "memory_modules.json",
        "storage": "storage_devices.json"
    }
    
    data = {}
    for key, filename in files.items():
        path = os.path.join(base_path, filename) if os.path.exists('data') else filename
        with open(path, 'r', encoding='utf-8') as f:
            data[key] = json.load(f)
    
    # 预处理：为板卡添加标签
    add_tags_to_motherboards(data["m_models"])
    return data

# --- 初始化数据 ---
data = load_data()

st.title("🖥️ DIY-PC 智能硬件配置系统")
st.markdown("---")

# 侧边栏：配置总览
st.sidebar.header("📋 我的配置单")
total_price = 0

# --- 第一步：选择处理器 (CPU) ---
st.header("1. 选择处理器")
col1, col2 = st.columns([1, 3])

with col1:
    brand = st.radio("选择平台", ["Intel", "AMD"])
    cpu_list = data["cpus"]["Intel_Processors"] if brand == "Intel" else data["cpus"]["AMD_Processors"]
    cpu_model = st.selectbox("选择型号", [c["model"] for c in cpu_list])

selected_cpu = next(c for c in cpu_list if c["model"] == cpu_model)
with col2:
    st.info(f"**规格:** {selected_cpu['specs']} | **接口:** {selected_cpu['socket']} | **层级:** {selected_cpu['tier'].upper()}")
    price = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price")
    st.metric("价格", f"￥{price}")
    total_price += price

# --- 第二步：选择主板 (Motherboard) ---
st.header("2. 选择主板")
# 根据 CPU 针脚过滤兼容的系列
compatible_series = [s["series"] for s in data["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
# 过滤具体的型号
compatible_boards = [b for b in data["m_models"]["motherboard_models"] if b["series"] in compatible_series]

if not compatible_boards:
    st.warning("暂无兼容的主板数据。")
    selected_board = None
else:
    board_model = st.selectbox("选择主板型号 (已根据接口过滤)", [f"{b['brand']} {b['model']}" for b in compatible_boards])
    selected_board = next(b for b in compatible_boards if f"{b['brand']} {b['model']}" == board_model)
    
    # 显示标签 (由 tagger.py 生成)
    tags_html = "".join([f'<span style="background-color:#007bff;color:white;padding:2px 6px;border-radius:4px;margin-right:5px;font-size:12px">{t}</span>' for t in selected_board.get('tags', [])])
    st.markdown(tags_html, unsafe_allow_html=True)
    st.metric("主板价格", f"￥{selected_board['price']}")
    total_price += selected_board["price"]

# --- 第三步：选择内存 (Memory) ---
st.header("3. 选择内存")
# 根据主板标签判断 DDR4 或 DDR5
required_ddr = "DDR5"
if selected_board and "DDR4" in selected_board.get("tags", []):
    required_ddr = "DDR4"
elif selected_board:
    # 从系列数据中获取默认 DDR 类型
    series_info = next(s for s in data["m_series"]["Motherboard_Series"] if s["series"] == selected_board["series"])
    required_ddr = series_info["ddr"]

# 内存数据结构预处理 (解决 JSON 中列表嵌套字典的问题)
mem_dict = data["memory"]["memory_modules"][0]
compatible_mem = [m for m in mem_dict.values() if m["type"] == required_ddr]

mem_display = st.selectbox(f"选择内存 (推荐 {required_ddr})", [m["display_name"] for m in compatible_mem])
selected_mem = next(m for m in compatible_mem if m["display_name"] == mem_display)

st.write(f"规格: {selected_mem['frequency']}MHz | 容量: {selected_mem['capacity']}GB")
st.metric("内存价格", f"￥{selected_mem['price']}")
total_price += selected_mem["price"]

# --- 第四步：选择存储 (Storage) ---
st.header("4. 选择硬盘")
storage_list = data["storage"]["storage_devices"]
storage_display = st.selectbox("选择硬盘", [s["display_name"] for s in storage_list])
selected_storage = next(s for s in storage_list if s["display_name"] == storage_display)

st.write(f"类型: {selected_storage['type']} | 容量: {selected_storage['capacity']}GB")
st.metric("硬盘价格", f"￥{selected_storage['price']}")
total_price += selected_storage["price"]

# --- 侧边栏总结 ---
st.sidebar.markdown("---")
st.sidebar.subheader(f"总预算: :red[￥{total_price}]")
if st.sidebar.button("保存配置"):
    st.sidebar.success("配置已暂存（此功能需配合数据库实现）")

st.sidebar.write("**配置详情:**")
st.sidebar.write(f"- CPU: {selected_cpu['model']}")
st.sidebar.write(f"- 主板: {selected_board['model'] if selected_board else '未选择'}")
st.sidebar.write(f"- 内存: {selected_mem['display_name']}")
st.sidebar.write(f"- 硬盘: {selected_storage['display_name']}")
