import streamlit as st
import json
import re
from core.tagger import add_tags_to_motherboards

# =========================
# 0️⃣ 页面配置
# =========================
st.set_page_config(page_title="DIY-PC 智能导购 Pro", page_icon="🖥️", layout="wide")
st.title("🖥️ DIY-PC 硬件导购系统（Pro版）")

# =========================
# 1️⃣ 工具函数
# =========================
def generate_recommendation_notes(board):
    tags = board.get("tags", [])
    notes = []
    
    # 功能/定位映射表
    tag_map = {
        "WIFI": "✔ 支持 WiFi + 蓝牙无线连接",
        "DDR4": "✔ 支持 DDR4 内存（性价比平台）",
        "DDR5": "✔ 支持 DDR5 内存（新一代平台）",
        "PCIe5": "✔ 支持 PCIe 5.0（显卡/SSD高速通道）",
        "High-End": "🔥 顶级旗舰级主板（超强供电/超频能力）",
        "Gaming": "🎮 游戏定位主板（稳定 + 性能均衡）",
        "Value": "💰 性价比取向，适合主流用户",
        "Budget": "🧩 入门级主板（基础办公/轻度使用）",
        "Pro/Creator": "🎨 创意/生产力优化（设计/剪辑）",
        "White": "🤍 白色主题外观（适合白色机箱）",
        "RGB": "✨ 支持 RGB 灯效同步"
    }
    
    for tag, desc in tag_map.items():
        if tag in tags:
            notes.append(desc)
    return notes

# =========================
# 2️⃣ 数据加载
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
        with open('data/memory_modules.json', 'r', encoding='utf-8') as f:
            memory_db = json.load(f)
        with open('data/storage_devices.json', 'r', encoding='utf-8') as f:
            storage_db = json.load(f)
        return cpu_db, mb_series_db, mb_model_db, memory_db, storage_db
    except Exception as e:
        st.error(f"❌ 数据加载失败: {e}")
        return None, None, None, None, None

cpu_data, mb_series_data, mb_model_data, memory_data, storage_data = load_data()

# =========================
# 3️⃣ 数据解析与标准化
# =========================
def parse_cpu(cpu):
    model = cpu.get("model", "")
    specs = cpu.get("specs", "")
    model_upper = model.upper()

    # 品牌识别
    brand = "Intel" if any(x in model_upper for x in ["I3", "I5", "I7", "I9", "ULTRA"]) else "AMD"

    # 插槽识别
    socket = ""
    match = re.search(r'(\d{4})针', specs)
    if match: socket = f"LGA{match.group(1)}"
    if brand == "AMD":
        digits = "".join(re.findall(r'\d+', model))
        socket = "AM4" if digits.startswith(("1", "2", "3", "4", "5")) else "AM5"

    # 档次识别
    tier = "mid"
    if "I3" in model_upper or "R3" in model_upper: tier = "entry"
    elif "I7" in model_upper or "I9" in model_upper or "R7" in model_upper or "R9" in model_upper: tier = "high"

    # 核显识别
    igpu = not ("F" in model_upper if brand == "Intel" else "G" not in model_upper)
    price = cpu.get("tray_price") or cpu.get("boxed_price") or 0

    return {"model": model, "brand": brand, "socket": socket, "tier": tier, "igpu": igpu, "price": price}

def match_series(cpu, series_list):
    tier_map = {"entry": 1, "mid": 2, "high": 3}
    cpu_tier = tier_map.get(cpu["tier"], 2)
    candidates = []
    for mb in series_list:
        if mb["socket"] != cpu["socket"]: continue
        score = 3 if tier_map.get(mb["tier"], 2) == cpu_tier else (1 if tier_map.get(mb["tier"], 2) > cpu_tier else -2)
        candidates.append((score, mb))
    candidates.sort(reverse=True, key=lambda x: x[0])
    return [c[1] for c in candidates[:3]]

# =========================
# 4️⃣ 主逻辑
# =========================
if all([cpu_data, mb_series_data, mb_model_data, memory_data, storage_data]):
    
    # 数据预处理
    cpu_list = [parse_cpu(c) for c in (cpu_data.get("Intel_Processors", []) + cpu_data.get("AMD_Processors", []))]
    series_list = [s for s in mb_series_data.get("Motherboard_Series", [])]
    model_list = mb_model_data.get("motherboard_models", [])

    # 布局：左侧参数选择
    brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)
    filtered_cpus = [c for c in cpu_list if c["brand"] == brand]
    
    selected_cpu_name = st.selectbox("选择处理器型号", [c["model"] for c in filtered_cpus])
    selected_cpu = next(c for c in filtered_cpus if c["model"] == selected_cpu_name)

    st.divider()

    col1, col2 = st.columns([1, 1])

    # --- 左列：核心配置信息 ---
    with col1:
        st.subheader("📋 已选硬件详情")
        st.info(f"**CPU:** {selected_cpu['model']} ({selected_cpu['socket']})")
        if selected_cpu["price"]:
            st.metric("CPU 价格", f"￥{selected_cpu['price']}")
        
        # 匹配主板
        matched_series = match_series(selected_cpu, series_list)
        if matched_series:
            selected_series = st.selectbox("选择推荐主板系列", [s["series"] for s in matched_series])
            filtered_models = [m for m in model_list if m["series"] == selected_series]
            
            if filtered_models:
                selected_mb_name = st.selectbox("选择具体型号", [m["model"] for m in filtered_models])
                mb_raw = next(m for m in filtered_models if m["model"] == selected_mb_name)
                
                # 打标签
                mb_with_tags = add_tags_to_motherboards({"motherboard_models": [mb_raw]})["motherboard_models"][0]
                
                st.success(f"🎯 主板已确认：{mb_with_tags['model']}")
                st.metric("主板价格", f"￥{mb_with_tags['price']}")
                
                # 推荐理由
                with st.expander("查看推荐理由"):
                    notes = generate_recommendation_notes(mb_with_tags)
                    for n in notes: st.write(n)
            else:
                st.warning("该系列暂无具体型号")
                mb_with_tags = None
        else:
            st.error("未找到匹配的主板系列")
            mb_with_tags = None

    # --- 右列：存储与内存 ---
    with col2:
        if mb_with_tags:
            # 1. 内存选择 (基于主板标签过滤)
            st.subheader("🧠 内存选择")
            mem_type = "DDR5" if "DDR5" in mb_with_tags.get("tags", []) else "DDR4"
            compatible_mem = [m for m in memory_data if m["type"] == mem_type]
            
            if compatible_mem:
                selected_mem_name = st.selectbox(f"选择 {mem_type} 内存", [m["display_name"] for m in compatible_mem])
                selected_mem = next(m for m in compatible_mem if m["display_name"] == selected_mem_name)
                st.metric("内存价格", f"￥{selected_mem['price']}")
            else:
                st.warning(f"暂无兼容的 {mem_type} 内存数据")
                selected_mem = {"price": 0}

            # 2. 硬盘选择
            st.subheader("💾 硬盘选择")
            
            selected_store_name = st.selectbox("选择固态硬盘", [s["display_name"] for s in storage_data["storage_devices"]])
            
         
            selected_store = next(s for s in storage_data["storage_devices"] if s["display_name"] == selected_store_name)

            
            st.metric("硬盘价格", f"￥{selected_store['price']}")

            # 3. 总价结算
            st.divider()
            total = (selected_cpu["price"] or 0) + (mb_with_tags["price"] or 0) + \
                    (selected_mem["price"] or 0) + (selected_store["price"] or 0)
            
            st.markdown(f"### 💰 核心四件套预估总价")
            st.title(f"￥{int(total)}")
            
            if st.button("生成配置清单"):
                st.balloons()
                st.code(f"""
                【DIY-PC 配置清单】
                --------------------------
                处理器: {selected_cpu['model']}
                主板:   {mb_with_tags['model']}
                内存:   {selected_mem.get('display_name', '未选择')}
                硬盘:   {selected_store['display_name']}
                --------------------------
                总计:   ￥{int(total)}
                """)

# =========================
# Sidebar
# =========================
st.sidebar.markdown("---")
st.sidebar.caption("💡 v2.5：核心四件套导购系统")
st.sidebar.caption("- 自动识别 CPU 针脚与等级")
st.sidebar.caption("- 自动过滤 DDR4/DDR5 内存兼容性")
st.sidebar.caption("- 支持实时总价计算")
