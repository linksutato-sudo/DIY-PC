import streamlit as st
import json
import re
from core.tagger import add_tags_to_motherboards

st.set_page_config(page_title="DIY-PC 智能导购 Pro", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统（Pro版）")


# =========================
# 推荐解释
# =========================
def generate_recommendation_notes(board):
    tags = board.get("tags", [])
    notes = []

    if "WIFI" in tags:
        notes.append("✔ 支持 WiFi + 蓝牙无线连接")

    if "DDR4" in tags:
        notes.append("✔ 支持 DDR4 内存（性价比平台）")
    elif "DDR5" in tags:
        notes.append("✔ 支持 DDR5 内存（新一代平台）")

    if "PCIe5" in tags:
        notes.append("✔ 支持 PCIe 5.0（高速通道）")

    if "High-End" in tags:
        notes.append("🔥 旗舰级主板（供电/扩展强）")

    if "Gaming" in tags:
        notes.append("🎮 游戏优化")

    if "Value" in tags:
        notes.append("💰 性价比优先")

    if "Budget" in tags:
        notes.append("🧩 入门定位")

    if "RGB" in tags:
        notes.append("✨ 支持 RGB")

    return notes


# =========================
# 数据加载
# =========================
@st.cache_data
def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            cpu_db = json.load(f)

        with open('data/motherboards_series.json', 'r', encoding='utf-8') as f:
            mb_series_db = json.load(f)

        with open('data/motherboard_models.json', 'r', encoding='utf-8') as f:
            mb_model_db = json.load(f)

        with open('data/storage_devices.json', 'r', encoding='utf-8') as f:
            storage_db = json.load(f)

        with open('data/memory_modules.json', 'r', encoding='utf-8') as f:
            memory_db = json.load(f)

        return cpu_db, mb_series_db, mb_model_db, storage_db, memory_db

    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        return None, None, None, None, None


cpu_data, mb_series_data, mb_model_data, storage_data, memory_data = load_data()


# =========================
# CPU解析
# =========================
def parse_cpu(cpu):
    model = cpu.get("model", "")
    specs = cpu.get("specs", "")
    model_upper = model.upper()

    if any(x in model_upper for x in ["I3", "I5", "I7", "I9"]):
        brand = "Intel"
    elif "R" in model_upper or "锐龙" in model:
        brand = "AMD"
    else:
        brand = "Unknown"

    socket = ""
    match = re.search(r'(\d{4})针', specs)
    if match:
        socket = f"LGA{match.group(1)}"

    if brand == "AMD":
        digits = "".join(re.findall(r'\d+', model))
        if digits.startswith(("1", "2", "3", "4", "5")):
            socket = "AM4"
        else:
            socket = "AM5"

    tier = "mid"
    if "I3" in model_upper:
        tier = "entry"
    elif "I5" in model_upper:
        tier = "mid"
    elif "I7" in model_upper or "I9" in model_upper:
        tier = "high"

    if "R7" in model_upper or "R9" in model_upper:
        tier = "high"

    igpu = True
    if "F" in model_upper:
        igpu = False

    price = cpu.get("tray_price") or cpu.get("boxed_price") or 0

    return {
        "model": model,
        "brand": brand,
        "socket": socket,
        "tier": tier,
        "igpu": igpu,
        "price": price
    }


# =========================
# 标准化
# =========================
def normalize_series(m):
    return {
        "series": m.get("series"),
        "socket": m.get("socket"),
        "tier": m.get("tier"),
    }


def normalize_model(m):
    return {
        "series": m.get("series"),
        "model": m.get("model"),
        "price": m.get("price", 0)
    }


def normalize_memory(m):
    return {
        "name": m.get("display_name"),
        "type": m.get("type"),
        "capacity": m.get("capacity"),
        "price": m.get("price", 0)
    }


def normalize_storage(s):
    return {
        "name": s.get("display_name"),
        "pcie": s.get("pcie"),
        "capacity": s.get("capacity"),
        "price": s.get("price", 0)
    }


# =========================
# 匹配
# =========================
def match_series(cpu, series_list):
    result = []
    for s in series_list:
        if s["socket"] == cpu["socket"]:
            result.append(s)
    return result[:3]


def get_models(series, model_list):
    return [m for m in model_list if m["series"] == series]


# =========================
# 主逻辑
# =========================
if cpu_data:

    cpu_list_raw = cpu_data.get("Intel_Processors", []) + cpu_data.get("AMD_Processors", [])
    cpu_list = [parse_cpu(c) for c in cpu_list_raw]

    series_list = [normalize_series(m) for m in mb_series_data["Motherboard_Series"]]
    model_list = [normalize_model(m) for m in mb_model_data["motherboard_models"]]

    memory_list = [normalize_memory(m) for m in memory_data]
    storage_list = [normalize_storage(s) for s in storage_data]

    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
    cpus = [c for c in cpu_list if c["brand"] == brand]

    selected_cpu_name = st.selectbox("选择CPU", [c["model"] for c in cpus])
    cpu = next(c for c in cpus if c["model"] == selected_cpu_name)

    st.divider()

    col1, col2 = st.columns(2)

    # CPU
    with col1:
        st.subheader("CPU")
        st.write(cpu["model"])
        st.metric("价格", f"￥{cpu['price']}")

    # 主板
    with col2:
        st.subheader("主板")

        series = match_series(cpu, series_list)
        series_name = st.selectbox("系列", [s["series"] for s in series])

        models = get_models(series_name, model_list)
        model_name = st.selectbox("型号", [m["model"] for m in models])

        mb = next(m for m in models if m["model"] == model_name)

        st.metric("主板价格", f"￥{mb['price']}")

        mb_with_tags = add_tags_to_motherboards({"motherboard_models": [mb]})["motherboard_models"][0]

        notes = generate_recommendation_notes(mb_with_tags)

        for n in notes:
            st.write(n)

    # =========================
    # 内存（智能过滤）
    # =========================
    st.divider()
    st.subheader("🧠 内存")

    if "DDR5" in mb_with_tags.get("tags", []):
        memory_list = [m for m in memory_list if m["type"] == "DDR5"]
    else:
        memory_list = [m for m in memory_list if m["type"] == "DDR4"]

    mem_name = st.selectbox("选择内存", [m["name"] for m in memory_list])
    mem = next(m for m in memory_list if m["name"] == mem_name)

    st.metric("内存价格", f"￥{mem['price']}")

    # =========================
    # 硬盘
    # =========================
    st.divider()
    st.subheader("💾 固态硬盘")

    ssd_name = st.selectbox("选择SSD", [s["name"] for s in storage_list])
    ssd = next(s for s in storage_list if s["name"] == ssd_name)

    st.metric("SSD价格", f"￥{ssd['price']}")

    # =========================
    # 总价
    # =========================
    total = cpu["price"] + mb["price"] + mem["price"] + ssd["price"]

    st.divider()
    st.success(f"💰 整机价格：￥{int(total)}")


# =========================
# sidebar
# =========================
st.sidebar.markdown("---")
st.sidebar.caption("v3：CPU + 主板 + 内存 + 硬盘")
