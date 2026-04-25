import streamlit as st
import json

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")
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
# 2️⃣ 数据标准化（兼容旧JSON）
# =========================
def normalize_cpu(cpu):
    """兼容你旧的数据结构"""
    return {
        "model": cpu.get("model"),
        "brand": cpu.get("brand", "AMD" if "Ryzen" in cpu.get("model", "") else "Intel"),
        "socket": cpu.get("socket") or cpu.get("supported_socket", ""),
        "tier": cpu.get("tier", "mid"),
        "igpu": cpu.get("igpu", False),
        "price": cpu.get("tray_price") or cpu.get("boxed_price") or 0
    }


def normalize_mb(mb):
    return {
        "series": mb.get("series"),
        "brand": mb.get("brand", "Intel" if "Intel" in mb.get("series", "") else "AMD"),
        "socket": mb.get("socket"),
        "tier": mb.get("tier", "mid"),
        "ddr": mb.get("ddr", ""),
        "reference_price": mb.get("reference_price", 0)
    }


# =========================
# 3️⃣ 推荐算法（核心）
# =========================
def match_motherboards(cpu, mb_list):
    candidates = []

    tier_map = {"entry": 1, "mid": 2, "high": 3}

    for mb in mb_list:
        # 1️⃣ 插槽必须一致
        if not cpu["socket"] or mb["socket"] != cpu["socket"]:
            continue

        score = 0

        cpu_tier = tier_map.get(cpu["tier"], 2)
        mb_tier = tier_map.get(mb["tier"], 2)

        # 2️⃣ 档次匹配
        if mb_tier == cpu_tier:
            score += 3
        elif mb_tier > cpu_tier:
            score += 1
        else:
            score -= 2

        # 3️⃣ IGPU
        if cpu.get("igpu"):
            score += 1

        # 4️⃣ 价格匹配
        if cpu["price"] and mb["reference_price"]:
            gap = abs(cpu["price"] - mb["reference_price"])
            score += max(0, 3 - gap / 500)

        candidates.append((score, mb))

    candidates.sort(reverse=True, key=lambda x: x[0])
    return [mb for _, mb in candidates[:3]]


# =========================
# 4️⃣ 主逻辑
# =========================
if cpu_data and mb_data:

    # 自动识别键
    cpu_key = next(iter(cpu_data))
    cpu_list_raw = cpu_data[cpu_key]

    mb_list_raw = mb_data.get("Motherboard_Series", [])

    # 标准化
    cpu_list = [normalize_cpu(c) for c in cpu_list_raw]
    mb_list = [normalize_mb(m) for m in mb_list_raw]

    # 平台选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)

    filtered_cpus = [c for c in cpu_list if c["brand"] == brand]

    if not filtered_cpus:
        st.warning("没有该平台CPU数据")
        st.stop()

    # 选择CPU
    selected_model = st.selectbox(
        "选择处理器型号",
        [c["model"] for c in filtered_cpus]
    )

    selected_cpu = next(c for c in filtered_cpus if c["model"] == selected_model)

    # =========================
    # 5️⃣ 展示CPU
    # =========================
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 处理器信息")
        st.write(f"**型号:** {selected_cpu['model']}")
        st.write(f"**平台:** {selected_cpu['brand']}")
        st.write(f"**插槽:** {selected_cpu['socket'] or '未知'}")

        if selected_cpu["price"]:
            st.metric("参考价格", f"￥{selected_cpu['price']}")

    # =========================
    # 6️⃣ 主板推荐
    # =========================
    with col2:
        st.subheader("🔌 主板推荐")

        if not selected_cpu["socket"]:
            st.warning("⚠️ CPU缺少 socket 信息，无法匹配")
        else:
            matched = match_motherboards(selected_cpu, mb_list)

            if matched:
                for mb in matched:
                    st.success(f"{mb['series']}（推荐）")
                    st.metric("主板价格", f"￥{mb['reference_price']}")

                    if selected_cpu["price"]:
                        total = selected_cpu["price"] + mb["reference_price"]
                        st.markdown(f"💰 套装价：`￥{total}`")

                    st.divider()
            else:
                st.warning("暂无匹配主板")

# =========================
# 7️⃣ 侧边栏
# =========================
st.sidebar.markdown("---")
st.sidebar.caption("💡 已升级为结构化推荐系统（非关键词匹配）")
st.sidebar.caption("数据来源：本地JSON / 店面报价")
