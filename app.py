import streamlit as st
import json
import re
from core.tagger import add_tags_to_motherboards
import json

st.set_page_config(page_title="DIY-PC 智能导购 Pro", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统（Pro版）")


# =========================
# 1️⃣ 数据加载
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

        return cpu_db, mb_series_db, mb_model_db

    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        return None, None, None


cpu_data, mb_series_data, mb_model_data = load_data()


# =========================
# 2️⃣ CPU 解析
# =========================
def parse_cpu(cpu):
    model = cpu.get("model", "")
    specs = cpu.get("specs", "")
    model_upper = model.upper()

    # brand
    if any(x in model_upper for x in ["I3", "I5", "I7", "I9", "ULTRA"]):
        brand = "Intel"
    elif "R" in model_upper or "锐龙" in model:
        brand = "AMD"
    else:
        brand = "Unknown"

    # socket
    socket = ""
    match = re.search(r'(\d{4})针', specs)
    if match:
        socket = f"LGA{match.group(1)}"

    if brand == "AMD":
        digits = "".join(re.findall(r'\d+', model))
        if digits.startswith(("1", "2", "3", "4", "5")):
            socket = "AM4"
        elif digits.startswith(("7", "8", "9")):
            socket = "AM5"

    # tier
    tier = "mid"
    if brand == "Intel":
        if "I3" in model_upper:
            tier = "entry"
        elif "I5" in model_upper:
            tier = "mid"
        elif "I7" in model_upper or "I9" in model_upper:
            tier = "high"
    elif brand == "AMD":
        if "R5" in model_upper:
            tier = "mid"
        elif "R7" in model_upper or "R9" in model_upper:
            tier = "high"

    # igpu
    igpu = True
    if brand == "Intel" and "F" in model_upper:
        igpu = False
    if brand == "AMD" and "G" not in model_upper:
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
# 3️⃣ 主板系列标准化
# =========================
def normalize_series(mb):
    return {
        "series": mb.get("series"),
        "brand": mb.get("brand", ""),
        "socket": mb.get("socket"),
        "tier": mb.get("tier", "mid"),
        "reference_price": mb.get("reference_price", 0)
    }


# =========================
# 4️⃣ 主板型号标准化
# =========================
def normalize_model(m):
    return {
        "series": m.get("series"),
        "model": m.get("model"),
        "brand": m.get("brand", ""),
        "price": m.get("price", 0)
    }


# =========================
# 5️⃣ 第一层：匹配 series
# =========================
def match_series(cpu, series_list):
    tier_map = {"entry": 1, "mid": 2, "high": 3}
    cpu_tier = tier_map.get(cpu["tier"], 2)

    candidates = []

    for mb in series_list:
        if mb["socket"] != cpu["socket"]:
            continue

        score = 0
        mb_tier = tier_map.get(mb["tier"], 2)

        if mb_tier == cpu_tier:
            score += 3
        elif mb_tier > cpu_tier:
            score += 1
        else:
            score -= 2

        candidates.append((score, mb))

    candidates.sort(reverse=True, key=lambda x: x[0])
    return [c[1] for c in candidates[:3]]


# =========================
# 6️⃣ 第二层：筛型号
# =========================
def get_models(series, model_list):
    return [m for m in model_list if m["series"] == series]


# =========================
# 7️⃣ 主逻辑
# =========================
if cpu_data and mb_series_data and mb_model_data:

    cpu_list_raw = cpu_data.get("Intel_Processors", []) + cpu_data.get("AMD_Processors", [])
    series_raw = mb_series_data.get("Motherboard_Series", [])
    model_raw = mb_model_data.get("motherboard_models", [])

    cpu_list = [parse_cpu(c) for c in cpu_list_raw]
    series_list = [normalize_series(m) for m in series_raw]
    model_list = [normalize_model(m) for m in model_raw]

    # 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)

    filtered_cpus = [c for c in cpu_list if c["brand"] == brand]

    if not filtered_cpus:
        st.warning("没有该平台CPU数据")
        st.stop()

    # CPU选择
    selected_model = st.selectbox("选择处理器型号", [c["model"] for c in filtered_cpus])
    selected_cpu = next(c for c in filtered_cpus if c["model"] == selected_model)

    st.divider()

    col1, col2 = st.columns(2)

    # =========================
    # CPU信息
    # =========================
    with col1:
        st.subheader("📋 处理器信息")
        st.write(f"**型号:** {selected_cpu['model']}")
        st.write(f"**平台:** {selected_cpu['brand']}")
        st.write(f"**插槽:** {selected_cpu['socket']}")
        st.write(f"**档次:** {selected_cpu['tier']}")
        st.write(f"**核显:** {'有' if selected_cpu['igpu'] else '无'}")

        if selected_cpu["price"]:
            st.metric("CPU价格", f"￥{selected_cpu['price']}")

    # =========================
    # 主板推荐（两层结构）
    # =========================
    with col2:
        st.subheader("🔌 主板推荐（分层选择）")

        matched_series = match_series(selected_cpu, series_list)

        if not matched_series:
            st.warning("暂无匹配主板系列")
        else:
            series_options = [s["series"] for s in matched_series]
            selected_series = st.selectbox("选择主板系列", series_options)

            # 第二层：型号
            filtered_models = get_models(selected_series, model_list)

            if not filtered_models:
                st.warning("该系列暂无具体型号")
            else:
                model_names = [m["model"] for m in filtered_models]
                selected_mb_model = st.selectbox("选择具体主板型号", model_names)

                mb = next(m for m in filtered_models if m["model"] == selected_mb_model)

                st.success(f"🎯 已选择：{mb['model']}")
                st.metric("主板价格", f"￥{mb['price']}")

                if selected_cpu["price"]:
                    total = selected_cpu["price"] + mb["price"]
                    st.markdown(f"💰 套装价：`￥{int(total)}`")

# 读取数据
with open("data/motherboard_models.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 生成 tags（关键一步）
data = add_tags_to_motherboards(data)

boards = data["motherboard_models"]

# UI展示
for b in boards:
    st.write(b["model"])
    st.write("标签：", ", ".join(b["tags"]))
    st.divider()
# =========================
# sidebar
# =========================
st.sidebar.markdown("---")
st.sidebar.caption("💡 v2：CPU解析 + Series → Model 两级推荐")
st.sidebar.caption("适用于装机报价 / 门店导购 / 配置生成")
