import streamlit as st
import json
import os
from tagger import add_tags_to_motherboards

# 页面配置
st.set_page_config(page_title="DIY-PC 智能装机助手", page_icon="🖥️", layout="wide")

# --- 数据加载与预处理 ---
@st.cache_data
def load_all_data():
    # 假设 JSON 文件都在同一目录下
    files = {
        "cpus": "cpus.json",
        "m_series": "motherboards_series.json",
        "m_models": "motherboard_models.json",
        "memory": "memory_modules.json",
        "storage": "storage_devices.json"
    }
    
    loaded_data = {}
    for key, filename in files.items():
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_data[key] = json.load(f)
        else:
            st.error(f"找不到文件: {filename}")
            return None

    # 核心步骤：调用 tagger.py 给主板打上标签（DDR4/5, WIFI等）
    add_tags_to_motherboards(loaded_data["m_models"])
    return loaded_data

data = load_all_data()

# --- 侧边栏：实时配置单 ---
st.sidebar.title("🛒 我的配置清单")
st.sidebar.markdown("---")
total_price = 0

# --- 主界面 ---
st.title("🖥️ DIY-PC 硬件导购系统")
st.caption("基于实时数据与兼容性逻辑的装机指南")

if data:
    # 1. 处理器 (CPU) 选择
    st.header("1. 选择处理器")
    cpu_col1, cpu_col2 = st.columns([1, 2])
    
    with cpu_col1:
        platform = st.radio("平台选择", ["Intel", "AMD"], horizontal=True)
        cpu_list = data["cpus"]["Intel_Processors"] if platform == "Intel" else data["cpus"]["AMD_Processors"]
        cpu_names = [c["model"] for c in cpu_list]
        selected_cpu_name = st.selectbox("搜索型号", cpu_names)
        
    selected_cpu = next(item for item in cpu_list if item["model"] == selected_cpu_name)
    
    with cpu_col2:
        st.info(f"**规格**: {selected_cpu['specs']}  \n**接口**: {selected_cpu['socket']} | **等级**: {selected_cpu['tier'].upper()}")
        cpu_price = selected_cpu.get("tray_price") or selected_cpu.get("boxed_price")
        st.metric("CPU 价格", f"￥{cpu_price}")
        total_price += cpu_price
        st.sidebar.write(f"**CPU:** {selected_cpu_name} (￥{cpu_price})")

    st.markdown("---")

    # 2. 主板 (Motherboard) 选择 - 自动过滤兼容接口
    st.header("2. 选择主板")
    # 逻辑：只显示 socket 匹配的主板系列
    compatible_series = [s["series"] for s in data["m_series"]["Motherboard_Series"] if s["socket"] == selected_cpu["socket"]]
    # 逻辑：从型号库中筛选出属于这些系列的主板
    compatible_boards = [b for b in data["m_models"]["motherboard_models"] if b["series"] in compatible_series]
    
    if not compatible_boards:
        st.warning(f"目前数据库中暂无兼容 {selected_cpu['socket']} 接口的主板。")
        selected_board = None
    else:
        board_col1, board_col2 = st.columns([1, 2])
        with board_col1:
            board_names = [f"{b['brand']} {b['model']}" for b in compatible_boards]
            selected_board_full = st.selectbox("选择兼容主板", board_names)
            selected_board = next(b for b in compatible_boards if f"{b['brand']} {b['model']}" == selected_board_full)
        
        with board_col2:
            # 显示 Tagger 生成的标签
            tags = selected_board.get("tags", [])
            tag_html = "".join([f'<span style="background-color:#2e7d32; color:white; padding:2px 8px; border-radius:10px; margin-right:5px; font-size:12px;">{t}</span>' for t in tags])
            st.markdown(tag_html, unsafe_allow_html=True)
            st.metric("主板价格", f"￥{selected_board['price']}")
            total_price += selected_board["price"]
            st.sidebar.write(f"**主板:** {selected_board['model']} (￥{selected_board['price']})")

    st.markdown("---")

    # 3. 内存 (Memory) 选择 - 自动匹配 DDR 类型
    st.header("3. 选择内存")
    if selected_board:
        # 逻辑：根据主板标签判断是 DDR4 还是 DDR5
        is_ddr4 = "DDR4" in selected_board.get("tags", [])
        target_type = "DDR4" if is_ddr4 else "DDR5"
        
        # 内存数据嵌套在列表的第一项字典里
        mem_pool = data["memory"]["memory_modules"][0]
        compatible_mem = [m for m in mem_pool.values() if m["type"] == target_type]
        
        mem_col1, mem_col2 = st.columns([1, 2])
        with mem_col1:
            mem_names = [m["display_name"] for m in compatible_mem]
            selected_mem_name = st.selectbox(f"选择 {target_type} 内存", mem_names)
            selected_mem = next(m for m in compatible_mem if m["display_name"] == selected_mem_name)
        
        with mem_col2:
            st.write(f"**频率**: {selected_mem['frequency']}MHz | **容量**: {selected_mem['capacity']}GB")
            st.metric("内存价格", f"￥{selected_mem['price']}")
            total_price += selected_mem["price"]
            st.sidebar.write(f"**内存:** {selected_mem['display_name']} (￥{selected_mem['price']})")
    else:
        st.write("请先选择主板以匹配内存。")

    st.markdown("---")

    # 4. 存储 (Storage) 选择
    st.header("4. 选择硬盘")
    storage_pool = data["storage"]["storage_devices"]
    storage_names = [s["display_name"] for s in storage_pool]
    
    st_col1, st_col2 = st.columns([1, 2])
    with st_col1:
        selected_st_name = st.selectbox("选择固态硬盘", storage_names)
        selected_storage = next(s for s in storage_pool if s["display_name"] == selected_st_name)
        
    with st_col2:
        st.write(f"**类型**: {selected_storage['type']} | **容量**: {selected_storage['capacity']}GB")
        st.metric("硬盘价格", f"￥{selected_storage['price']}")
        total_price += selected_storage["price"]
        st.sidebar.write(f"**硬盘:** {selected_storage['display_name']} (￥{selected_storage['price']})")

    # 总结
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"总计金额: :red[￥{total_price}]")
    if st.sidebar.button("保存配置清单", use_container_width=True):
        st.sidebar.success("配置已锁定（演示功能）")

else:
    st.warning("请检查数据文件是否存在。")
