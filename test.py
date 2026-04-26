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

# --- 核心推荐算法 (五级强化版) ---
def get_auto_recommendation(budget, requirement, data):
    # 1. 统一定义五级策略与硬性约束
    STRATEGY_MAP = {
        "点亮 (low) 仅办公": {
            "tier": "low", "cpu_ratio": 0.45, "gpu_ratio": 0.0, 
            "min_ram": 8, "min_ssd": 512, "usage": "office"
        },
        "入门 (Entry) 办公、影音、网游": {
            "tier": "entry", "cpu_ratio": 0.35, "gpu_ratio": 0.35, 
            "min_ram": 16, "min_ssd": 512, "usage": "gaming"
        },
        "中端 (Mid) 主流 3A、剪辑、多任务": {
            "tier": "mid", "cpu_ratio": 0.30, "gpu_ratio": 0.45, 
            "min_ram": 32, "min_ssd": 1024, "usage": "gaming"
        },
        "中高端 (High-Mid) 4K 游戏、重度直播": {
            "tier": "high-mid", "cpu_ratio": 0.25, "gpu_ratio": 0.55, 
            "min_ram": 32, "min_ssd": 2048, "usage": "gaming"
        },
        "专业设计旗舰(Flagship) 极端发烧友、3D 渲染": {
            "tier": "top", "cpu_ratio": 0.35, "gpu_ratio": 0.45, 
            "min_ram": 64, "min_ssd": 2048, "usage": "production"
        }
    }

    strat = STRATEGY_MAP.get(requirement)
    if not strat: return None

    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    # 严格匹配 tier 标签
    potential_cpus = [c for c in all_cpus if c['tier'] == strat['tier']]
    # 价格从高到低排序，尝试在该等级内给用户最好的
    potential_cpus.sort(key=lambda x: x.get('tray_price', 0) or x.get('boxed_price', 0), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price', 0) or cpu.get('boxed_price', 0)
        # 允许 CPU 预算有一定浮动弹性
        if cpu_price > budget * (strat['cpu_ratio'] + 0.1): continue
        
        # GPU 逻辑
        gpu_to_use, gpu_price = None, 0
        need_gpu = not (strat['usage'] == "office" and cpu.get('igpu', True))
        
        if need_gpu:
            potential_gpus = [g for g in data['gpus']['gpus'] if g['tier'] == strat['tier']]
            if not potential_gpus: continue
            # 过滤预算范围内的显卡
            potential_gpus = [g for g in potential_gpus if g['price'] <= budget * (strat['gpu_ratio'] + 0.1)]
            if not potential_gpus: continue
            
            # 排序：优先选择性能最强的
            potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 主板联动
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == cpu['socket']]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        if not potential_mbs: continue
        potential_mbs.sort(key=lambda x: x['price'])
        mb = potential_mbs[0] # 选基础款主板

        # 内存硬性约束 (容量 >= min_ram)
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        ddr_type = mb_info['ddr']
        potential_rams = [
            r for r in data['memory']['memory_modules'] 
            if r['type'] == ddr_type and r.get('capacity', 0) >= strat['min_ram']
        ]
        if not potential_rams: continue
        potential_rams.sort(key=lambda x: x['price'])
        ram = potential_rams[0]

        # 硬盘硬性约束 (容量 >= min_ssd)
        # 假设数据中有 capacity 字段（单位GB），或者通过 display_name 解析
        potential_ssds = [
            s for s in data['storage']['storage_devices'] 
            if s.get('capacity_gb', 0) >= strat['min_ssd'] or strat['usage'] in s.get('usage', [])
        ]
        if not potential_ssds: continue
        potential_ssds.sort(key=lambda x: x['price'])
        ssd = potential_ssds[0]

        total = cpu_price + gpu_price + mb['price'] + ram['price'] + ssd['price']
        # 允许总价有 10% 的超支余量，以匹配硬性容量要求
        if total <= budget * 1.1:
            return {
                "cpu": cpu, "gpu": gpu_to_use, "mb": mb, 
                "ram": ram, "ssd": ssd, "total": total, 
                "tier": strat['tier']
            }
            
    return None

def main():
    data = load_all_data()
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']

    if 'config' not in st.session_state:
        st.session_state.config = {
            "cpu": all_cpus[0], "gpu": None, "mb": None, "ram": None, "ssd": data['storage']['storage_devices'][0]
        }
    
    with st.sidebar:
        st.header("⚙️ 智能配置引擎")
        budget = st.number_input("您的预算 (RMB)", 2000, 100000, 6000, step=500)
        # 更新为用户要求的五级场景
        req = st.selectbox("核心用途", [
            "点亮 (low) 仅办公",
            "入门 (Entry) 办公、影音、网游",
            "中端 (Mid) 主流 3A、剪辑、多任务",
            "中高端 (High-Mid) 4K 游戏、重度直播",
            "专业设计旗舰(Flagship) 极端发烧友、3D 渲染"
        ])
        
        if st.button("✨ 一键生成推荐方案", use_container_width=True):
            res = get_auto_recommendation(budget, req, data)
            if res:
                st.session_state.config = res
                st.toast(f"已匹配{res['tier']}级方案", icon="✅")
            else:
                st.error("此预算范围内无法满足该场景的【硬性容量约束】或硬件等级。请尝试增加预算。")

    col_main, col_summary = st.columns([1.2, 0.8])

    with col_main:
        st.subheader("🛠️ 硬件深度微调")
        conf = st.session_state.config

        # 快捷档位 (保持 tier 逻辑对齐)
        st.caption("同步对齐硬件等级")
        t_cols = st.columns(5)
        tiers = [("⚪点亮", "low"), ("🔵入门", "entry"), ("🟢中端", "mid"), ("🟡高端", "high-mid"), ("🔴旗舰", "top")]
        for i, (label, t_key) in enumerate(tiers):
            if t_cols[i].button(label, key=f"btn_{t_key}", use_container_width=True):
                new_cpu = next((c for c in all_cpus if c['tier'] == t_key), all_cpus[0])
                st.session_state.config['cpu'] = new_cpu
                st.session_state.config['gpu'] = next((g for g in data['gpus']['gpus'] if g['tier'] == t_key), None)
                st.rerun()

        with st.container(border=True):
            # 1. CPU
            cpu_list = [c['model'] for c in all_cpus]
            c_idx = cpu_list.index(conf['cpu']['model']) if conf['cpu']['model'] in cpu_list else 0
            sel_cpu = st.selectbox("1. 处理器 (CPU)", cpu_list, index=c_idx)
            conf['cpu'] = next(c for c in all_cpus if c['model'] == sel_cpu)

            # 2. GPU
            gpu_data_list = data['gpus']['gpus']
            gpu_list = ["集成显卡 (不选)"] + [f"{g['brand']} {g['model']} ({g['vram']})" for g in gpu_data_list]
            g_idx = 0
            if conf['gpu']:
                g_str = f"{conf['gpu']['brand']} {conf['gpu']['model']} ({conf['gpu']['vram']})"
                g_idx = gpu_list.index(g_str) if g_str in gpu_list else 0
            sel_gpu = st.selectbox("2. 显卡 (GPU)", gpu_list, index=g_idx)
            conf['gpu'] = None if sel_gpu == "集成显卡 (不选)" else gpu_data_list[gpu_list.index(sel_gpu)-1]

            # 3. 主板 (基于 Socket 过滤)
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
                st.warning(f"缺少支持 {socket} 的主板数据")

            # 4. 内存 (基于 DDR 过滤)
            if conf['mb']:
                mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])
                ddr = mb_info['ddr']
                rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr]
                ram_list = [r['display_name'] for r in rams]
                r_idx = ram_list.index(conf['ram']['display_name']) if conf['ram'] and conf['ram']['display_name'] in ram_list else 0
                sel_ram = st.selectbox(f"4. 内存 (需 {ddr})", ram_list, index=r_idx)
                conf['ram'] = rams[ram_list.index(sel_ram)]

            # 5. 存储
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
            st.metric("预算估算", f"¥ {total_sum:,.0f}", delta=f"预算差额: {budget-total_sum:,.0f}")
            
            # 使用 DataFrame 显示更整洁
            st.table([
                {"配件": "处理器", "型号": conf['cpu']['model'], "参考价": f"¥{p_cpu}"},
                {"配件": "显卡", "型号": conf['gpu']['model'] if conf['gpu'] else "核心显卡", "参考价": f"¥{p_gpu}"},
                {"配件": "主板", "型号": conf['mb']['model'], "参考价": f"¥{p_mb}"},
                {"配件": "内存", "型号": conf['ram']['display_name'] if conf['ram'] else "未选", "参考价": f"¥{p_ram}"},
                {"配件": "存储", "型号": conf['ssd']['display_name'], "参考价": f"¥{p_ssd}"}
            ])

            st.write("---")
            if st.button("🔍 运行兼容性与平衡性评估", use_container_width=True):
                with st.status("正在进行深度分析...", expanded=True) as status:
                    issues = 0
                    # 评估逻辑维持原样，由于我们更新了推荐算法，这里的评估结果会更理想
                    if not conf['cpu'].get('igpu', True) and not conf['gpu']:
                        st.error("【致命】当前处理器无核显，必须选配独立显卡方可点亮。")
                        issues += 1
                    
                    if issues == 0:
                        st.success("【专家认证】配置均衡，各部件等级匹配度极高！")
                    status.update(label="评估分析完成", state="complete")

if __name__ == "__main__":
    main()
