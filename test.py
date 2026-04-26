import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 专家助手", layout="wide")

# 加载数据
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
        with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
            data[key] = json.load(f)
    return data

# 复用您原有的自动推荐逻辑作为“初始化”引擎
def get_auto_recommendation(budget, requirement, data):
    """
    基于五级分层体系的推荐逻辑：
    - 点亮 (low): 仅办公
    - 入门 (entry): 办公、影音、网游
    - 中端 (mid): 主流3A、剪辑、多任务
    - 中高端 (high-mid): 4K游戏、重度直播
    - 旗舰 (top): 发烧友、大模型、3D渲染
    """
    
    # 1. 策略映射：定义各场景的 目标层级、预算系数、用途标签
    STRATEGY_MAP = {
        "办公": {
            "target_tiers": ["low", "entry"],
            "ratios": {"cpu": 0.4, "gpu": 0.0, "other": 0.6},
            "usage": "office"
        },
        "网游/影音": {
            "target_tiers": ["entry", "mid"],
            "ratios": {"cpu": 0.35, "gpu": 0.35, "other": 0.3},
            "usage": "gaming"
        },
        "主流3A/剪辑": {
            "target_tiers": ["mid", "high-mid"],
            "ratios": {"cpu": 0.3, "gpu": 0.45, "other": 0.25},
            "usage": "gaming"
        },
        "4K游戏/直播": {
            "target_tiers": ["high-mid", "top"],
            "ratios": {"cpu": 0.25, "gpu": 0.55, "other": 0.2},
            "usage": "gaming"
        },
        "旗舰/渲染/AI": {
            "target_tiers": ["top"],
            "ratios": {"cpu": 0.4, "gpu": 0.4, "other": 0.2},
            "usage": "production"
        }
    }

    # 获取当前策略，如果匹配不到则默认为“主流3A/剪辑”
    strategy = STRATEGY_MAP.get(requirement, STRATEGY_MAP["主流3A/剪辑"])
    target_tiers = strategy["target_tiers"]
    ratios = strategy["ratios"]
    usage_tag = strategy["usage"]

    # 2. 筛选 CPU
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    # 过滤层级并初步限制价格
    potential_cpus = [c for c in all_cpus if c['tier'] in target_tiers]
    
    # 排序：优先匹配层级，再匹配预算内性能最强的（价格降序）
    potential_cpus.sort(key=lambda x: (target_tiers.index(x['tier']), x.get('tray_price', 0) or x.get('boxed_price', 0)), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price') or cpu.get('boxed_price', 0)
        if cpu_price > budget * (ratios['cpu'] + 0.1): # 允许10%浮动
            continue
        
        socket = cpu['socket']
        
        # 3. GPU 逻辑
        gpu_to_use = None
        gpu_price = 0
        # 如果是“办公”且CPU带核显，不选独显；否则必须选独显
        need_gpu = not (requirement == "办公" and cpu.get('igpu', True))
        
        if need_gpu:
            potential_gpus = [g for g in data['gpus']['gpus'] if g['price'] <= budget * (ratios['gpu'] + 0.1)]
            
            if not potential_gpus: continue
            
            # 排序策略：生产力看显存，游戏看核心性能（价格）
            if usage_tag == "production":
                potential_gpus.sort(key=lambda x: (int(x['vram'].split('GB')[0]), x['price']), reverse=True)
            else:
                potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 4. 匹配主板 (按接口匹配，选性价比最高的)
        valid_series = [s for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        series_names = [s['series'] for s in valid_series]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in series_names]
        
        if not potential_mbs: continue
        potential_mbs.sort(key=lambda x: x['price']) # 选最便宜能用的，给核心配件腾空间
        mb = potential_mbs[0]
        
        # 5. 匹配内存 (DDR类型严格匹配)
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        ddr_type = mb_info['ddr']
        
        potential_rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
        
        # 针对层级调整容量需求
        min_ram_gb = 8
        if "top" in target_tiers: min_ram_gb = 64
        elif "high-mid" in target_tiers: min_ram_gb = 32
        elif "mid" in target_tiers: min_ram_gb = 16
        
        potential_rams = [r for r in potential_rams if r.get('capacity', 0) >= min_ram_gb]
        if not potential_rams: continue
        potential_rams.sort(key=lambda x: x['price'])
        ram = potential_rams[0]

        # 6. 匹配存储 (根据用途筛选)
        potential_ssds = [s for s in data['storage']['storage_devices'] if usage_tag in s['usage']]
        potential_ssds.sort(key=lambda x: x['price'])
        if not potential_ssds: continue
        ssd = potential_ssds[0]

        # 7. 最终预算审核
        total = cpu_price + gpu_price + mb['price'] + ram['price'] + ssd['price']
        
        if total <= budget * 1.05: # 允许 5% 的超支余量
            return {
                "tier_category": target_tiers[-1], # 返回推荐的最高目标层级
                "cpu": cpu,
                "gpu": gpu_to_use,
                "mb": mb,
                "ram": ram,
                "ssd": ssd,
                "total": total
            }
                
    return None

def main():
    st.title("💻 DIY PC 智能配置 & 自选助手")
    data = load_all_data()

    # 1. 初始化 Session State
    if 'config' not in st.session_state:
        all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
        st.session_state.config = {
            "cpu": all_cpus[0], 
            "gpu": None, 
            "mb": None, 
            "ram": None, 
            "ssd": None
        }

    # 侧边栏：自动推荐控制
    with st.sidebar:
        st.header("⚙️ 自动推荐设置")
        budget = st.number_input("预算 (RMB)", 1000, 100000, 5000)
        # 场景选项对应 get_auto_recommendation 中的策略 Key
        req = st.selectbox("场景", ["办公", "网游/影音", "主流3A/剪辑", "4K游戏/直播", "旗舰/渲染/AI"])
        
        if st.button("生成/重置推荐方案"):
            res = get_auto_recommendation(budget, req, data)
            if res:
                st.session_state.config = res
                st.success(f"已生成【{res.get('tier_category', '').upper()}】级最优方案！")
            else:
                st.error("未找到匹配方案，请尝试调高预算。")

    # 2. 主界面布局
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🛠️ 配件手工微调")
        conf = st.session_state.config
        all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
        
        # --- 同步五级分层：快速快速选择 ---
        st.write("快速对齐性能等级：")
        btn_rows = st.columns(5) # 改为 5 列
        
        def quick_set_tier(target_tier):
            new_cpu = next((c for c in all_cpus if c['tier'] == target_tier), all_cpus[0])
            new_gpus = [g for g in data['gpus']['gpus'] if g['tier'] == target_tier]
            new_gpu = new_gpus[0] if new_gpus else None
            st.session_state.config['cpu'] = new_cpu
            st.session_state.config['gpu'] = new_gpu
            # 主板和内存会在下方联动
            st.rerun()

        tiers_info = [
            ("⚪ 点亮", "low"), ("🔵 入门", "entry"), ("🟢 中端", "mid"), 
            ("🟡 中高端", "high-mid"), ("🔴 旗舰", "top")
        ]
        
        for i, (label, t_key) in enumerate(tiers_info):
            if btn_rows[i].button(label, use_container_width=True):
                quick_set_tier(t_key)

        st.divider()

        # --- 配件选择逻辑 (保持联动) ---
        # CPU
        cpu_names = [c['model'] for c in all_cpus]
        curr_cpu_idx = cpu_names.index(conf['cpu']['model']) if conf['cpu'] and conf['cpu']['model'] in cpu_names else 0
        sel_cpu_name = st.selectbox("选择处理器 (CPU)", cpu_names, index=curr_cpu_idx)
        conf['cpu'] = next(c for c in all_cpus if c['model'] == sel_cpu_name)

        # GPU
        gpus = [None] + data['gpus']['gpus']
        gpu_display_names = ["集成显卡 (不选)"] + [f"{g['brand']} {g['model']} ({g['vram']})" for g in data['gpus']['gpus']]
        curr_gpu_idx = 0
        if conf['gpu']:
            target_gpu_name = f"{conf['gpu']['brand']} {conf['gpu']['model']} ({conf['gpu']['vram']})"
            curr_gpu_idx = gpu_display_names.index(target_gpu_name) if target_gpu_name in gpu_display_names else 0
        sel_gpu_name = st.selectbox("选择显卡 (GPU)", gpu_display_names, index=curr_gpu_idx)
        conf['gpu'] = gpus[gpu_display_names.index(sel_gpu_name)]

        # 主板 (联动 CPU Socket)
        socket = conf['cpu']['socket']
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        mb_names = [f"{m['brand']} {m['model']}" for m in mbs]
        curr_mb_idx = 0
        if conf['mb'] and f"{conf['mb']['brand']} {conf['mb']['model']}" in mb_names:
            curr_mb_idx = mb_names.index(f"{conf['mb']['brand']} {conf['mb']['model']}")
        
        if mb_names:
            sel_mb_name = st.selectbox(f"选择主板 ({socket})", mb_names, index=curr_mb_idx)
            conf['mb'] = mbs[mb_names.index(sel_mb_name)]
        else:
            st.error(f"❌ 缺少 {socket} 主板数据")
            conf['mb'] = None

        # 内存 (联动主板 DDR)
        if conf['mb']:
            mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])
            ddr_type = mb_info['ddr']
            rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            ram_names = [r['display_name'] for r in rams]
            curr_ram_idx = ram_names.index(conf['ram']['display_name']) if conf['ram'] and conf['ram']['display_name'] in ram_names else 0
            if ram_names:
                sel_ram_name = st.selectbox(f"选择内存 ({ddr_type})", ram_names, index=curr_ram_idx)
                conf['ram'] = rams[ram_names.index(sel_ram_name)]
        
        # 存储
        ssds = data['storage']['storage_devices']
        ssd_names = [s['display_name'] for s in ssds]
        curr_ssd_idx = ssd_names.index(conf['ssd']['display_name']) if conf['ssd'] and conf['ssd']['display_name'] in ssd_names else 0
        sel_ssd_name = st.selectbox("选择固态硬盘 (SSD)", ssd_names, index=curr_ssd_idx)
        conf['ssd'] = ssds[ssd_names.index(sel_ssd_name)]

    # 3. 结果汇总与五级评估逻辑
    with col2:
        st.subheader("📋 配置清单汇总")
        if not conf['cpu'] or not conf['mb']:
            st.info("请完成核心配件选择。")
        else:
            p_cpu = conf['cpu'].get('tray_price') or conf['cpu'].get('boxed_price', 0)
            p_gpu = conf['gpu']['price'] if conf['gpu'] else 0
            p_mb = conf['mb']['price'] if conf['mb'] else 0
            p_ram = conf['ram']['price'] if conf['ram'] else 0
            p_ssd = conf['ssd']['price'] if conf['ssd'] else 0
            total = p_cpu + p_gpu + p_mb + p_ram + p_ssd
            
            st.metric("总价估计", f"¥{total:,.2f}")
            
            summary_table = [
                ["CPU", conf['cpu']['model'], f"¥{p_cpu}"],
                ["GPU", conf['gpu']['model'] if conf['gpu'] else "核显/集成", f"¥{p_gpu}"],
                ["主板", conf['mb']['model'], f"¥{p_mb}"],
                ["内存", conf['ram']['display_name'] if conf['ram'] else "未选", f"¥{p_ram}"],
                ["硬盘", conf['ssd']['display_name'] if conf['ssd'] else "未选", f"¥{p_ssd}"]
            ]
            st.table(summary_table)

            if st.button("🔍 执行专家评估报告", use_container_width=True):
                with st.status("正在进行深度分析...", expanded=True) as status:
                    has_issue = False
                    
                    # 1. 层级权重定义 (支持五级)
                    tw = {"low": 1, "entry": 2, "mid": 3, "high-mid": 4, "top": 5}
                    cpu_w = tw.get(conf['cpu'].get('tier'), 0)
                    gpu_w = tw.get(conf['gpu'].get('tier'), 0) if conf['gpu'] else 1
                    
                    # 2. 瓶颈分析
                    if gpu_w > cpu_w + 1:
                        st.warning("【瓶颈】显卡级别过高，CPU 可能会限制显卡在高帧率下的发挥。")
                        has_issue = True
                    elif cpu_w > gpu_w + 1 and req != "办公":
                        st.warning("【瓶颈】CPU 级别过高，游戏性能主要受限于显卡。")
                        has_issue = True

                    # 3. 内存与场景匹配
                    ram_cap = conf['ram'].get('capacity', 0) if conf['ram'] else 0
                    if req in ["4K游戏/直播", "旗舰/渲染/AI"] and ram_cap < 32:
                        st.error(f"【配置不足】对于{req}场景，{ram_cap}GB 内存将成为严重瓶颈。")
                        has_issue = True
                    elif req == "主流3A/剪辑" and ram_cap < 16:
                        st.warning("【建议】主流游戏及剪辑建议 16GB 内存起步。")
                        has_issue = True

                    # 4. 核显点亮校验
                    if not conf['cpu'].get('igpu', True) and not conf['gpu']:
                        st.error("【致命错误】F系列/无核显CPU 必须搭配独立显卡才能点亮！")
                        has_issue = True

                    # 5. 存储容量预警
                    if req != "办公" and conf['ssd'] and "512GB" in conf['ssd']['display_name']:
                        st.info("【容量提示】当前 SSD 容量较小，安装数个 3A 游戏或大型素材后可能空间不足。")

                    if not has_issue:
                        st.success("【专家认证】配置均衡，各部件等级匹配度极高！")
                    
                    status.update(label="评估分析完成", state="complete")
