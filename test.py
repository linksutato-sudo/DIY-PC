import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 专家助手", layout="wide", page_icon="💻")

# --- 数据加载优化 ---
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
        except FileNotFoundError:
            st.error(f"无法找到数据文件: {filename}")
    return data

# --- 核心推荐算法 ---
def get_auto_recommendation(budget, requirement, data):
    STRATEGY_MAP = {
        "办公": {"target_tiers": ["low", "entry"], "ratios": {"cpu": 0.4, "gpu": 0.0}, "tag": "office"},
        "网游/影音": {"target_tiers": ["entry", "mid"], "ratios": {"cpu": 0.35, "gpu": 0.35}, "tag": "gaming"},
        "主流3A/剪辑": {"target_tiers": ["mid", "high-mid"], "ratios": {"cpu": 0.3, "gpu": 0.45}, "tag": "gaming"},
        "4K游戏/直播": {"target_tiers": ["high-mid", "top"], "ratios": {"cpu": 0.25, "gpu": 0.55}, "tag": "gaming"},
        "旗舰/渲染/AI": {"target_tiers": ["top"], "ratios": {"cpu": 0.4, "gpu": 0.4}, "tag": "production"}
    }

    strat = STRATEGY_MAP.get(requirement)
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    potential_cpus = [c for c in all_cpus if c['tier'] in strat['target_tiers']]
    # 按价格降序
    potential_cpus.sort(key=lambda x: x.get('tray_price', 0) or x.get('boxed_price', 0), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price', 0) or cpu.get('boxed_price', 0)
        if cpu_price > budget * (strat['ratios']['cpu'] + 0.15): continue
        
        # GPU 逻辑
        gpu_to_use, gpu_price = None, 0
        need_gpu = not (requirement == "办公" and cpu.get('igpu', True))
        if need_gpu:
            potential_gpus = [g for g in data['gpus']['gpus'] if g['price'] <= budget * (strat['ratios']['gpu'] + 0.15)]
            if not potential_gpus: continue
            # 排序：生产力看显存，游戏看价格
            sort_key = (lambda x: int(x['vram'].split('GB')[0])) if strat['tag'] == "production" else (lambda x: x['price'])
            potential_gpus.sort(key=sort_key, reverse=True)
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 主板联动
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == cpu['socket']]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        if not potential_mbs: continue
        potential_mbs.sort(key=lambda x: x['price'])
        mb = potential_mbs[0]

        # 内存与存储
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        ram = next((r for r in data['memory']['memory_modules'] if r['type'] == mb_info['ddr']), None)
        ssd = next((s for s in data['storage']['storage_devices'] if strat['tag'] in s['usage']), data['storage']['storage_devices'][0])

        total = cpu_price + gpu_price + mb['price'] + (ram['price'] if ram else 0) + ssd['price']
        if total <= budget * 1.1:
            return {"cpu": cpu, "gpu": gpu_to_use, "mb": mb, "ram": ram, "ssd": ssd, "total": total, "tier": strat['target_tiers'][-1]}
    return None

def main():
    data = load_all_data()
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']

    # --- 1. 初始化 Session State ---
    if 'config' not in st.session_state:
        st.session_state.config = {
            "cpu": all_cpus[0], "gpu": None, "mb": None, "ram": None, "ssd": data['storage']['storage_devices'][0]
        }
    
    # --- 2. 侧边栏 ---
    with st.sidebar:
        st.header("⚙️ 智能配置引擎")
        budget = st.number_input("您的预算 (RMB)", 2000, 100000, 6000, step=500)
        req = st.selectbox("核心用途", ["办公", "网游/影音", "主流3A/剪辑", "4K游戏/直播", "旗舰/渲染/AI"])
        
        if st.button("✨ 一键生成推荐方案", use_container_width=True):
            res = get_auto_recommendation(budget, req, data)
            if res:
                st.session_state.config = res
                st.toast(f"已匹配{res['tier']}级方案", icon="✅")
            else:
                st.error("此预算范围内无法匹配该场景的最优配置，或缺少对应配件库存。请适当增加预算，或更换配置。")

    # --- 3. 主界面布局 ---
    col_main, col_summary = st.columns([1.2, 0.8])

    with col_main:
        st.subheader("🛠️ 硬件深度微调")
        conf = st.session_state.config

        # 快捷档位
        st.caption("同步对齐硬件等级")
        t_cols = st.columns(5)
        tiers = [("⚪点亮", "low"), ("🔵入门", "entry"), ("🟢中端", "mid"), ("🟡高端", "high-mid"), ("🔴旗舰", "top")]
        for i, (label, t_key) in enumerate(tiers):
            if t_cols[i].button(label, key=f"btn_{t_key}", use_container_width=True):
                new_cpu = next((c for c in all_cpus if c['tier'] == t_key), all_cpus[0])
                st.session_state.config['cpu'] = new_cpu
                st.session_state.config['gpu'] = next((g for g in data['gpus']['gpus'] if g['tier'] == t_key), None)
                st.rerun()

        # --- 核心自选逻辑 (联动修复) ---
        with st.container(border=True):
            # CPU
            cpu_list = [c['model'] for c in all_cpus]
            c_idx = cpu_list.index(conf['cpu']['model']) if conf['cpu']['model'] in cpu_list else 0
            sel_cpu = st.selectbox("1. 处理器 (CPU)", cpu_list, index=c_idx)
            conf['cpu'] = next(c for c in all_cpus if c['model'] == sel_cpu)

            # GPU
            gpu_list = ["集成显卡 (不选)"] + [f"{g['brand']} {g['model']} ({g['vram']})" for g in data['gpus']['gpus']]
            g_idx = 0
            if conf['gpu']:
                g_str = f"{conf['gpu']['brand']} {conf['gpu']['model']} ({conf['gpu']['vram']})"
                g_idx = gpu_list.index(g_str) if g_str in gpu_list else 0
            sel_gpu = st.selectbox("2. 显卡 (GPU)", gpu_list, index=g_idx)
            conf['gpu'] = None if sel_gpu == "集成显卡 (不选)" else data['gpus']['gpus'][gpu_list.index(sel_gpu)-1]

            # 主板 (基于 Socket 过滤)
            socket = conf['cpu']['socket']
            valid_mb_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
            mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_mb_series]
            mb_list = [f"{m['brand']} {m['model']}" for m in mbs]
            
            m_idx = 0
            if conf['mb'] and f"{conf['mb']['brand']} {conf['mb']['model']}" in mb_list:
                m_idx = mb_list.index(f"{conf['mb']['brand']} {conf['mb']['model']}")
            
            if mb_list:
                sel_mb = st.selectbox(f"3. 主板 (支持 {socket})", mb_list, index=m_idx)
                conf['mb'] = mbs[mb_list.index(sel_mb)]
            else:
                st.warning(f"缺少支持 {socket} 的主板")

            # 内存 (基于主板 DDR 过滤)
            if conf['mb']:
                mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])
                ddr = mb_info['ddr']
                rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr]
                ram_list = [r['display_name'] for r in rams]
                r_idx = ram_list.index(conf['ram']['display_name']) if conf['ram'] and conf['ram']['display_name'] in ram_list else 0
                sel_ram = st.selectbox(f"4. 内存 (需 {ddr})", ram_list, index=r_idx)
                conf['ram'] = rams[ram_list.index(sel_ram)]

            # 存储
            ssd_list = [s['display_name'] for s in data['storage']['storage_devices']]
            s_idx = ssd_list.index(conf['ssd']['display_name']) if conf['ssd'] and conf['ssd']['display_name'] in ssd_list else 0
            sel_ssd = st.selectbox("5. 存储 (SSD)", ssd_list, index=s_idx)
            conf['ssd'] = data['storage']['storage_devices'][ssd_list.index(sel_ssd)]

    with col_summary:
        st.subheader("📋 实时配置清单")
        if conf['cpu'] and conf['mb']:
            p_cpu = conf['cpu'].get('tray_price', 0) or conf['cpu'].get('boxed_price', 0)
            p_gpu = conf['gpu']['price'] if conf['gpu'] else 0
            p_mb = conf['mb']['price'] if conf['mb'] else 0
            p_ram = conf['ram']['price'] if conf['ram'] else 0
            p_ssd = conf['ssd']['price'] if conf['ssd'] else 0
            
            total_sum = p_cpu + p_gpu + p_mb + p_ram + p_ssd
            st.metric("预算估算 (含散片/板卡)", f"¥ {total_sum:,.0f}", delta=f"预算盈余: {budget-total_sum:,.0f}")
            
            summary_df = [
                {"配件": "处理器", "型号": conf['cpu']['model'], "参考价": f"¥{p_cpu}"},
                {"配件": "显卡", "型号": conf['gpu']['model'] if conf['gpu'] else "核心显卡", "参考价": f"¥{p_gpu}"},
                {"配件": "主板", "型号": conf['mb']['model'], "参考价": f"¥{p_mb}"},
                {"配件": "内存", "型号": conf['ram']['display_name'] if conf['ram'] else "未选", "参考价": f"¥{p_ram}"},
                {"配件": "存储", "型号": conf['ssd']['display_name'], "参考价": f"¥{p_ssd}"}
            ]
            st.table(summary_df)

            # --- 专家评估区域 ---
            st.write("---")
            if st.button("🔍 运行兼容性与平衡性评估", use_container_width=True):
                with st.status("正在进行深度分析...", expanded=True) as status:
                    issues = 0
                    tw = {"low": 1, "entry": 2, "mid": 3, "high-mid": 4, "top": 5}
                    c_w, g_w = tw.get(conf['cpu']['tier'], 0), tw.get(conf['gpu']['tier'] if conf['gpu'] else "low", 1)
                    
                    # 规则1: 点亮校验
                    if not conf['cpu'].get('igpu', True) and not conf['gpu']:
                        st.error("【致命】当前处理器无核显，必须选配独立显卡方可点亮。")
                        issues += 1
                    
                    # 规则2: 平衡性
                    if g_w > c_w + 1:
                        st.warning(f"【高分低能】显卡等级远超处理器，建议升级 CPU 以发挥显卡全部性能。")
                    
                    # 规则3: 内存
                    r_cap = conf['ram'].get('capacity', 0) if conf['ram'] else 0
                    if req in ["旗舰/渲染/AI", "4K游戏/直播"] and r_cap < 32:
                        st.error(f"【瓶颈】{req}建议至少 32GB 内存，当前 {r_cap}GB 严重不足。")
                        issues += 1
                    
                    if issues == 0:
                        st.success("【完美】经评估，该配置在目标场景下具有极佳的平衡性！")
                    status.update(label="评估分析完成", state="complete")

if __name__ == "__main__":
    main()
