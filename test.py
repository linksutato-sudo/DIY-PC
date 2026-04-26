import streamlit as st
import math

# --- 模拟辅助函数 (请确保你的代码中有这些) ---
def get_val(obj, key, default=0):
    return obj.get(key, default)

# --- 模拟数据结构 ---
SCENARIOS = {
    "办公/家用 (Low/Entry)": {"min": 0, "max": 3500, "rec_ram": 8, "rec_ssd": 512},
    "主流网游 (Entry/Mid)": {"min": 3501, "max": 6000, "rec_ram": 16, "rec_ssd": 1024},
    "单机大作 (High/Ultra)": {"min": 6001, "max": 15000, "rec_ram": 32, "rec_ssd": 1024},
    "生产力/工作站": {"min": 15001, "max": 1000000, "rec_ram": 64, "rec_ssd": 2048},
}

# --- 1. 侧边栏：配置参数入口 ---
with st.sidebar:
    st.header("第一步：设定预算")
    user_budget = st.number_input("您的预算 (￥)", min_value=2000, max_value=100000, value=6500, step=500)
    
    st.markdown("---")
    st.subheader("场景与性能微调")
    
    # 自动匹配默认场景索引
    default_idx = 0
    for i, (name, info) in enumerate(SCENARIOS.items()):
        if info["min"] <= user_budget <= info["max"]:
            default_idx = i
            break
            
    current_scenario = st.selectbox("当前匹配场景", list(SCENARIOS.keys()), index=default_idx)
    
    # 性能等级微调：直接影响推荐逻辑
    perf_level = st.select_slider("性能等级微调", options=["Low", "Standard", "High"], value="Standard")
    
    # 根据场景和微调计算最终推荐值
    scenario_info = SCENARIOS[current_scenario].copy()
    if perf_level == "Low":
        scenario_info["rec_ram"] = max(8, scenario_info["rec_ram"] // 2)
    elif perf_level == "High":
        scenario_info["rec_ram"] *= 2
        scenario_info["rec_ssd"] = max(1024, scenario_info["rec_ssd"] * 2)

    st.info(f"💡 场景需求：{scenario_info['rec_ram']}GB 内存 | {scenario_info['rec_ssd']}GB 存储")

# --- 2. 核心逻辑处理 (假设已有 CPU 价格) ---
cpu_p = 1500.0  # 示例数据

# --- 3. 渲染展示区 ---
st.title("🖥️ DIY PC 场景化平衡配置专家")

col1, col2 = st.columns([2, 1])

with col1:
    # --- 显卡与主板选择 (示例数据) ---
    gpu = st.selectbox("选择显卡", [{"price": 2500, "brand": "NVIDIA", "chipset": "RTX 4060"}], 
                       format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['chipset']}")
    mb = st.selectbox("选择主板", [{"price": 800, "brand": "华硕", "model": "B760M"}], 
                      format_func=lambda x: f"￥{get_val(x, 'price')} - {x['brand']} {x['model']}")
    
    st.markdown("---")
    st.subheader("存储扩展 (已根据场景自动推荐数量)")
    
    # --- 内存自动推荐 ---
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        # 假设 available_mem 已经从你的 JSON 加载
        mem = st.selectbox("选择内存型号", available_mem, 
                           format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
    with col_m2:
        single_unit_cap = get_val(mem, 'capacity', 8)
        # 动态计算推荐数量
        auto_mem_count = max(1, math.ceil(scenario_info["rec_ram"] / single_unit_cap))
        if get_val(mem, 'sticks', 1) >= 2:
            auto_mem_count = 1
            
        # 【修复关键】：key 随场景和推荐值变化，强制刷新默认值
        mem_count = st.number_input("数量", 1, 8, value=int(auto_mem_count), 
                                    key=f"mem_cnt_{current_scenario}_{scenario_info['rec_ram']}")

    # --- 硬盘自动推荐 ---
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        ssd = st.selectbox("选择硬盘型号", available_ssd, 
                           format_func=lambda x: f"￥{get_val(x, 'price')} - {x['display_name']}")
    with col_s2:
        single_ssd_cap = get_val(ssd, 'capacity', 1024)
        # 容差逻辑：95% 满足即推荐 1 个
        auto_ssd_count = max(1, math.ceil((scenario_info["rec_ssd"] * 0.95) / single_ssd_cap))
        
        ssd_count = st.number_input("数量", 1, 4, value=int(auto_ssd_count), 
                                    key=f"ssd_cnt_{current_scenario}_{scenario_info['rec_ssd']}")

with col2:
    # --- 实际容量计算 ---
    actual_mem_total = get_val(mem, 'capacity', 0) * mem_count
    actual_ssd_total = get_val(ssd, 'capacity', 0) * ssd_count

    # --- 价格看板 ---
    total_price = cpu_p + get_val(gpu, 'price') + get_val(mb, 'price') + \
                  (get_val(mem, 'price') * mem_count) + (get_val(ssd, 'price') * ssd_count)
    
    st.metric("方案总价", f"￥{total_price:.2f}")
    st.metric("预算剩余", f"￥{user_budget - total_price:.2f}", delta=f"{user_budget - total_price:.2f}")

    st.write("### ⚖️ 配置平衡性报告")
    
    # 核心组件配比判定
    gpu_ratio = get_val(gpu, 'price') / cpu_p if cpu_p > 0 else 1
    if gpu_ratio > 4: st.warning("⚠️ 显卡过强，CPU可能存在性能瓶颈。")
    elif gpu_ratio < 0.5: st.warning("⚠️ CPU过强，显卡可能无法完全发挥。")
    else: st.success("✅ 核心组件配比科学。")
    
    # 内存容量判定
    if actual_mem_total < scenario_info["rec_ram"]:
        st.error(f"❌ 内存不足: 当前 {actual_mem_total}GB < 推荐 {scenario_info['rec_ram']}GB")
    else:
        st.success(f"✅ 内存充足: 已达 {actual_mem_total}GB")

    # 硬盘容量判定 (使用容差解决 1000 < 1024 问题)
    if actual_ssd_total < (scenario_info["rec_ssd"] * 0.95):
        st.info(f"📂 存储较小: 当前 {actual_ssd_total}GB < 建议 {scenario_info['rec_ssd']}GB")
    else:
        st.success(f"✅ 存储充足: 已达 {actual_ssd_total}GB")
    
    st.write("---")
    st.caption(f"当前配置适用于: {current_scenario} ({perf_level} Mode)")
