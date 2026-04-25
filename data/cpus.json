import streamlit as st
import json
import re

st.set_page_config(page_title="DIY-PC 智能导购 Pro", page_icon="🖥️")
st.title("🖥️ DIY-PC 硬件导购系统（Pro版）")

# =========================
# 1️⃣ 数据加载
# =========================
def load_data():
    try:
        with open('data/cpus.json', 'r', encoding='utf-8') as f:
            cpu_db = json.load(f)

        with open('data/motherboards.json', 'r', encoding='utf-8') as f:
            mb_db = json.load(f)

        return cpu_db, mb_db

    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        return None, None


cpu_data, mb_data = load_data()


# =========================
# 2️⃣ CPU 自动解析系统（核心）
# =========================
def parse_cpu(cpu):
    model = cpu.get("model", "")
    specs = cpu.get("specs", "")

    model_upper = model.upper()

    # ===== 品牌 =====
    if any(x in model_upper for x in ["I3", "I5", "I7", "I9", "ULTRA"]):
        brand = "Intel"
    elif "R" in model_upper or "锐龙" in model:
        brand = "AMD"
    else:
        brand = "Unknown"

    # ===== socket =====
    socket = ""

    # Intel：从 specs 解析
    match = re.search(r'(\d{4})针', specs)
    if match:
        socket = f"LGA{match.group(1)}"

    # AMD：根据代际判断
    if brand == "AMD":
        digits = "".join(re.findall(r'\d+', model))
        if digits.startswith(("1", "2", "3", "4", "5")):
            socket = "AM4"
        elif digits.startswith(("7", "8", "9")):
            socket = "AM5"

    # ===== tier =====
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
        elif "R7" in model_upper:
            tier = "high"
        elif "R9" in model_upper:
            tier = "high"

    # ===== 核显 =====
    igpu = True

    if brand == "Intel":
        if "F" in model_upper:
            igpu = False

    elif brand == "AMD":
        if "G" in model_upper:
            igpu = True
        else:
            igpu = False

    # ===== 价格 =====
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
# 3️⃣ 主板标准化
# =========================
def normalize_mb(mb):
    return {
        "series": mb.get("series"),
        "brand": mb.get("brand", ""),
        "socket": mb.get("socket"),
        "tier": mb.get("tier", "mid"),
        "reference_price": mb.get("reference_price", 0)
    }


# =========================
# 4️⃣ 推荐算法
# =========================
def match_motherboards(cpu, mb_list):
    candidates = []

    tier_map = {"entry": 1, "mid": 2, "high": 3}

    for mb in mb_list:

        # 插槽必须一致
        if not cpu["socket"] or mb["socket"] != cpu["socket"]:
            continue

        score = 0

        cpu_tier = tier_map.get(cpu["tier"], 2)
        mb_tier = tier_map.get(mb["tier"], 2)

        # 档次匹配
        if mb_tier == cpu_tier:
            score += 3
        elif mb_tier > cpu_tier:
            score += 1
        else:
            score -= 2

        # 核显加分（未来可扩展）
        if cpu["igpu"]:
            score += 1

        # 价格匹配
        if cpu["price"] and mb["reference_price"]:
            gap = abs(cpu["price"] - mb["reference_price"])
            score += max(0, 3 - gap / 500)

        candidates.append((score, mb))

    candidates.sort(reverse=True, key=lambda x: x[0])
    return [mb for _, mb in candidates[:3]]


# =========================
# 5️⃣ 主逻辑
# =========================
if cpu_data and mb_data:

    cpu_list_raw = cpu_data.get("Intel_Processors", []) + cpu_data.get("AMD_Processors", [])
    mb_list_raw = mb_data.get("Motherboard_Series", [])

    cpu_list = [parse_cpu(c) for c in cpu_list_raw]
    mb_list = [normalize_mb(m) for m in mb_list_raw]

    # 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)

    filtered_cpus = [c for c in cpu_list if c["brand"] == brand]

    if not filtered_cpus:
        st.warning("没有该平台CPU数据")
        st.stop()

    # 选择 CPU
    selected_model = st.selectbox("选择处理器型号", [c["model"] for c in filtered_cpus])
    selected_cpu = next(c for c in filtered_cpus if c["model"] == selected_model)

    # =========================
    # 显示 CPU
    # =========================
    st.divider()
    col1, col2 = st.columns(2)

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
    # 主板推荐
    # =========================
    with col2:
        st.subheader("🔌 主板推荐")

        matched = match_motherboards(selected_cpu, mb_list)

        if matched:
            for mb in matched:
                st.success(f"{mb['series']}（推荐）")
                st.metric("主板价格", f"￥{mb['reference_price']}")

                if selected_cpu["price"]:
                    total = selected_cpu["price"] + mb["reference_price"]
                    st.markdown(f"💰 套装价：`￥{int(total)}`")

                st.divider()
        else:
            st.warning("暂无匹配主板")

# =========================
# 侧边栏
# =========================
st.sidebar.markdown("---")
st.sidebar.caption("💡 已启用：自动CPU解析 + 结构化推荐")
st.sidebar.caption("适用于电脑店装机 / 报价辅助")
