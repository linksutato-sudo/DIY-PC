import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 专家助手 Pro", layout="wide", page_icon="💻")

# --- 数据加载 ---
@st.cache_data
def load_all_data():
    base_path = "data"
    files = {
        "cpus": "cpus.json",
        "memory": "memory_modules.json",
        "mb_models": "motherboard_models.json",
        "mb_series": "motherboards_series.json",
        "storage": "storage_devices.json",
        "gpus": "gpus.json"
    }
    data = {}
    for key, filename in files.items():
        try:
            with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
                data[key] = json.load(f)
        except Exception as e:
            st.error(f"加载 {filename} 失败: {e}")
    return data

# --- 核心推荐算法（五级分层强化版） ---
def get_auto_recommendation(budget, requirement, data):
    """
    配置策略字典：
    target_tier: 对应数据中的 tier 标签
    ratios: 核心配件预算占比
    min_ram: 最低内存要求 (GB)
    min_ssd: 最低硬盘要求 (GB)
    """
    STRATEGY_MAP = {
        "点亮 (Low)": {
            "target_tier": "low",
            "ratios": {"cpu": 0.45, "gpu": 0.0}, 
            "min_ram": 8, "min_ssd": 512, "tag": "office"
        },
        "入门 (Entry)": {
            "target_tier": "entry",
            "ratios": {"cpu": 0.35, "gpu": 0.35}, 
            "min_ram": 16, "min_ssd": 512, "tag": "gaming"
        },
        "中端 (Mid)": {
            "target_tier": "mid",
            "ratios": {"cpu": 0.30, "gpu": 0.45}, 
            "min_ram": 32, "min_ssd": 1024, "tag": "gaming"
        },
        "中高端 (High-Mid)": {
            "target_tier": "high-mid",
            "ratios": {"cpu": 0.25, "gpu": 0.55}, 
            "min_ram": 32, "min_ssd": 2048, "tag": "gaming"
        },
        "专业设计旗舰 (Flagship)": {
            "target_tier": "top", # 假设数据中顶级标签为 top 或 flagship
            "ratios": {"cpu": 0.35, "gpu": 0.45}, 
            "min_ram": 64, "min_ssd": 2048, "tag": "production"
        }
    }

    strat = STRATEGY_MAP.get(requirement)
    if not strat: return None

    # 1. 筛选 CPU (严格匹配 Tier)
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    potential_cpus = [c for c in all_cpus if c['tier'] == strat['target_tier']]
    # 按价格降序排序，优先尝试性能更好的（预算内最贵的）
    potential_cpus.sort(key=lambda x: x.get('tray_price', 0) or x.get('boxed_price', 0), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price', 0) or cpu.get('boxed_price', 0)
        # CPU 预算保护：不允许超过分配比例的 120%
        if cpu_price > budget * (strat['ratios']['cpu'] * 1.2): continue
        
        # 2. 筛选 GPU
        gpu_to_use, gpu_price = None, 0
        need_gpu = not (strat['target_tier'] == "low" and cpu.get('igpu', True))
        
        if need_gpu:
            potential_gpus = [g for g in data['gpus']['gpus'] if g['tier'] == strat['target_tier']]
            # 如果该层级没找到显卡，尝试稍微低一级或高一级的（可选逻辑，此处保持严格匹配）
            if not potential_gpus: continue
            
            # 过滤超预算的显卡
            potential_gpus = [g for g in potential_gpus if g['price'] <= budget * (strat['ratios']['gpu'] * 1.2)]
            if not potential_gpus: continue
            
            # 排序：旗舰看显存和价格，其余看价格
            potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 3. 匹配主板 (基于 Socket 联动)
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == cpu['socket']]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        if not potential_mbs: continue
        # 主板选该系列中价格适中的（index 中间位），避免用顶级CPU配最廉价主板
        potential_mbs.sort(key=lambda x: x['price'])
        mb = potential_mbs[len(potential_mbs)//2] if len(potential_mbs) > 1 else potential_mbs[0]
        
        # 4. 匹配内存 (DDR类型匹配 + 容量阈值)
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        ddr_type = mb_info['ddr']
        potential_rams = [
            r for r in data['memory']['memory_modules'] 
            if r['type'] == ddr_type and r.get('capacity', 0) >= strat['min_ram']
        ]
        if not potential_rams: continue
        potential_rams.sort(key=lambda x: x['price'])
        ram = potential_rams[0] # 选性价比最高的满足容量的内存

        # 5. 匹配存储 (用途标签 + 容量阈值)
        potential_ssds = [
            s for s in data['storage']['storage_devices'] 
            if s.get('capacity_gb', 0) >= strat['min_ssd']
        ]
        if not potential_ssds: continue
        potential_ssds.sort(key=lambda x: x['price'])
        ssd = potential_ssds[0]

        # 6. 总价检查 (允许 10% 浮动)
        total = cpu_price + gpu_price + mb['price'] + ram['price'] + ssd['price']
        if total <= budget * 1.1:
            return {
                "cpu": cpu, "gpu": gpu_to_use, "mb": mb, 
                "ram": ram, "ssd": ssd, "total": total, 
                "tier": strat['target_tier']
            }
            
    return None

def main():
    data = load_all_data()
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']

    # --- 1. Session State 初始化 ---
    if 'config' not in st.session_state:
        st.session_state.config = {
            "cpu": all_cpus[0], "gpu": None, "mb": None, 
            "ram": None, "ssd": data['storage']['storage_devices'][0]
        }
    
    # --- 2. 侧边栏控制 ---
    with st.sidebar:
        st.header("⚙️ 智能配置设定")
        user_budget = st.number_input("您的预算 (RMB)", 2000, 100000, 6000, step=500)
        user_req = st.selectbox("使用场景", [
            "点亮 (Low)", "入门 (Entry)", "中端 (Mid)", 
            "中高端 (High-Mid)", "专业设计旗舰 (Flagship)"
        ])
        
        if st.button("🚀 生成五级对齐推荐", use_container_width=True):
            res = get_auto_recommendation(user_budget, user_req, data)
            if res:
                st.session_state.config = res
                st.success(f"已成功匹配 {user_req} 方案")
            else:
                st.error("当前预算无法满足该等级的硬性参数（如内存/硬盘容量），请提升预算。")

    # --- 3. 页面展示 ---
    col_left, col_right = st.columns([1.2, 0.8])
    conf = st.session_state.config

    with col_left:
        st.subheader("🛠️ 配件微调")
        # CPU 选择
        cpu_list = [c['model'] for c in all_cpus]
        c_idx = cpu_list.index(conf['cpu']['model']) if conf['cpu']['model'] in cpu_list else 0
        sel_cpu = st.selectbox("处理器 (CPU)", cpu_list, index=c_idx)
        conf['cpu'] = next(c for c in all_cpus if c['model'] == sel_cpu)

        # GPU 选择
        gpu_data_list = data['gpus']['gpus']
        gpu_display = ["集成显卡 / 无独显"] + [f"{g['brand']} {g['model']} ({g['vram']})" for g in gpu_data_list]
        g_idx = 0
        if conf['gpu']:
            g_str = f"{conf['gpu']['brand']} {conf['gpu']['model']} ({conf['gpu']['vram']})"
            g_idx = gpu_display.index(g_str) if g_str in gpu_display else 0
        sel_gpu = st.selectbox("显卡 (GPU)", gpu_display, index=g_idx)
        conf['gpu'] = None if sel_gpu == "集成显卡 / 无独显" else gpu_data_list[gpu_display.index(sel_gpu)-1]

        # 主板/内存/硬盘 (此处省略冗余逻辑，与之前保持一致)
        # ... [保留之前代码中的联动逻辑] ...

    with col_right:
        st.subheader("📋 配置单详情")
        p_cpu = conf['cpu'].get('tray_price', 0) or conf['cpu'].get('boxed_price', 0)
        p_gpu = conf['gpu']['price'] if conf['gpu'] else 0
        p_mb = conf['mb']['price'] if conf['mb'] else 0
        p_ram = conf['ram']['price'] if conf['ram'] else 0
        p_ssd = conf['ssd']['price'] if conf['ssd'] else 0
        total_price = p_cpu + p_gpu + p_mb + p_ram + p_ssd
        
        st.metric("预估总价", f"¥ {total_price:,.2f}")
        
        # 简单表格展示
        st.dataframe([
            {"组件": "CPU", "型号": conf['cpu']['model'], "价格": p_cpu},
            {"组件": "显卡", "型号": conf['gpu']['model'] if conf['gpu'] else "核显", "价格": p_gpu},
            {"组件": "主板", "型号": conf['mb']['model'] if conf['mb'] else "未选", "价格": p_mb},
            {"组件": "内存", "型号": conf['ram']['display_name'] if conf['ram'] else "未选", "价格": p_ram},
            {"组件": "硬盘", "型号": conf['ssd']['display_name'], "价格": p_ssd},
        ], use_container_width=True)

if __name__ == "__main__":
    main()
