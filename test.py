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
    # 1. 策略定义：根据场景分配预算比例和目标等级
    if requirement == "游戏":
        cpu_ratio, gpu_ratio = 0.3, 0.6
        target_tiers = ["mid", "high"]
        usage_tag = "gaming"
    elif requirement == "生产力":
        cpu_ratio, gpu_ratio = 0.45, 0.4
        target_tiers = ["high"]
        usage_tag = "production"
    else:  # 办公
        cpu_ratio, gpu_ratio = 0.4, 0.0
        target_tiers = ["entry", "mid"]
        usage_tag = "office"

    # 2. 筛选 CPU
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    potential_cpus = [c for c in all_cpus if c['tier'] in target_tiers 
                      and (c.get('tray_price') or c.get('boxed_price', 0)) <= budget * cpu_ratio]
    
    # CPU 按价格降序排列，优先选该预算段内最强的
    potential_cpus.sort(key=lambda x: x.get('tray_price') or x.get('boxed_price', 0), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price') or cpu.get('boxed_price', 0)
        socket = cpu['socket']
        
        # 3. GPU 逻辑：判定是否需要独立显卡
        need_gpu = not cpu.get('igpu', True) or requirement in ["游戏", "生产力"]
        gpu_to_use = None
        gpu_price = 0
        
        if need_gpu:
            # 筛选显卡
            potential_gpus = [g for g in data['gpus']['gpus'] 
                             if usage_tag in g['usage'] and g['price'] <= budget * gpu_ratio]
            
            if not potential_gpus:
                continue # 预算内买不起显卡，尝试下一个 CPU
            
            # --- 核心区别：排序策略 ---
            if requirement == "生产力":
                # 生产力看重显存大小（解析 VRAM 字符串中的数字）
                potential_gpus.sort(key=lambda x: int(x['vram'].split('GB')[0]), reverse=True)
            else:
                # 游戏和办公看重核心性能（通常价格正相关）
                potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 4. 匹配主板 (根据 Socket)
        valid_series = [s for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        series_names = [s['series'] for s in valid_series]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in series_names]
        
        if not potential_mbs: continue
        potential_mbs.sort(key=lambda x: x['price'])
        mb = potential_mbs[0]

      # 5. 匹配内存 (根据主板 DDR 类型及场景需求)
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        ddr_type = mb_info['ddr']
        
        # 初始筛选：匹配 DDR 类型 (DDR4/DDR5)
        potential_rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
        
        # --- 针对场景的容量硬性过滤与排序策略 ---
        if requirement == "游戏":
            # 游戏场景：起步 16G，价格优先 (寻找性价比最高的 16G+)
            potential_rams = [r for r in potential_rams if r.get('capacity', 0) >= 16]
            potential_rams.sort(key=lambda x: x['price'])
            
        elif requirement == "生产力":
            # 生产力场景：起步 32G，容量优先 (大内存对生产力至关重要)
            potential_rams = [r for r in potential_rams if r.get('capacity', 0) >= 32]
            # 先按容量降序，容量相同时按价格升序
            potential_rams.sort(key=lambda x: (-x.get('capacity', 0), x['price']))
            
        else:  # 办公/默认
            # 办公场景：8G 起步即可，极致性价比优先
            potential_rams.sort(key=lambda x: x['price'])
        
        # 获取最终匹配结果
        ram = potential_rams[0] if potential_rams else None

        # 6. 匹配存储
        potential_ssds = [s for s in data['storage']['storage_devices'] if usage_tag in s['usage']]
        potential_ssds.sort(key=lambda x: x['price'])

        # 7. 预算终审
        if potential_rams and potential_ssds:
            ram = potential_rams[0]
            ssd = potential_ssds[0]
            total = cpu_price + gpu_price + mb['price'] + ram['price'] + ssd['price']
            
            if total <= budget:
                return {
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

    # 1. 初始化 Session State (如果不存在则赋予初始默认值)
    if 'config' not in st.session_state:
        # 为了防止首次加载报错，给一个基础默认值（如库中第一个CPU）
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
        budget = st.number_input("预算 (RMB)", 1000, 50000, 5000)
        # 定义 req 变量，供后续专家评估使用
        req = st.selectbox("场景", ["办公", "游戏", "生产力"])
        
        if st.button("生成/重置推荐方案"):
            res = get_auto_recommendation(budget, req, data)
            if res:
                st.session_state.config = res
                st.success("已生成最优兼容方案！")
            else:
                st.error("未找到匹配方案")

    # 2. 主界面
    col1, col2 = st.columns([2, 1])

    # 2. 主界面：配件自选区
    with col1:
        st.subheader("🛠️ 配件手工微调")
        conf = st.session_state.config
        all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
        
        # --- 新增：性能定位快捷快速选择 ---
        st.write("快速对齐性能等级：")
        btn_cols = st.columns(3)
        
        # 快速设置逻辑
        def quick_set_tier(target_tier):
            # 找到对应等级的第一个 CPU 和 GPU
            new_cpu = next((c for c in all_cpus if c['tier'] == target_tier), all_cpus[0])
            new_gpus = [g for g in data['gpus']['gpus'] if g['tier'] == target_tier]
            new_gpu = new_gpus[0] if new_gpus else None
            
            # 更新全局配置
            st.session_state.config['cpu'] = new_cpu
            st.session_state.config['gpu'] = new_gpu
            # 注意：主板和内存会在下方的联动逻辑中自动跟随 CPU 更新
            st.rerun()

        if btn_cols[0].button("🔵 入门级 (Entry)", use_container_width=True):
            quick_set_tier("entry")
        if btn_cols[1].button("🟢 中端级 (Mid)", use_container_width=True):
            quick_set_tier("mid")
        if btn_cols[2].button("🔴 高端级 (High)", use_container_width=True):
            quick_set_tier("high")

        st.divider()

        # --- CPU 选择 ---
        cpu_names = [c['model'] for c in all_cpus]
        curr_cpu_idx = cpu_names.index(conf['cpu']['model']) if conf['cpu'] and conf['cpu']['model'] in cpu_names else 0
        sel_cpu_name = st.selectbox("选择处理器 (CPU)", cpu_names, index=curr_cpu_idx)
        conf['cpu'] = next(c for c in all_cpus if c['model'] == sel_cpu_name)

        # --- GPU 选择 ---
        gpus = [None] + data['gpus']['gpus']
        gpu_display_names = ["集成显卡 (不选)"] + [f"{g['brand']} {g['model']} ({g['vram']})" for g in data['gpus']['gpus']]
        
        curr_gpu_idx = 0
        if conf['gpu']:
            target_gpu_name = f"{conf['gpu']['brand']} {conf['gpu']['model']} ({conf['gpu']['vram']})"
            if target_gpu_name in gpu_display_names:
                curr_gpu_idx = gpu_display_names.index(target_gpu_name)
        
        sel_gpu_name = st.selectbox("选择显卡 (GPU)", gpu_display_names, index=curr_gpu_idx)
        conf['gpu'] = gpus[gpu_display_names.index(sel_gpu_name)]

        # --- 主板选择 (基于 CPU Socket 联动) ---
        socket = conf['cpu']['socket']
        # 筛选支持该接口的系列
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        # 筛选具体的型号
        mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        mb_names = [f"{m['brand']} {m['model']}" for m in mbs]
        
        curr_mb_idx = 0
        if conf['mb']:
            target_mb_name = f"{conf['mb']['brand']} {conf['mb']['model']}"
            if target_mb_name in mb_names:
                curr_mb_idx = mb_names.index(target_mb_name)
            else:
                curr_mb_idx = 0 # 接口不匹配时，重置为主板列表第一个
        
        if mb_names:
            sel_mb_name = st.selectbox(f"选择主板 (支持接口: {socket})", mb_names, index=curr_mb_idx)
            conf['mb'] = mbs[mb_names.index(sel_mb_name)]
        else:
            st.error(f"❌ 警告：库中暂无支持 {socket} 接口的主板！")
            conf['mb'] = None

        # --- 内存选择 (基于主板 DDR 类型联动) ---
        if conf['mb']:
            # 获取当前主板所属系列的 DDR 规格
            mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])
            ddr_type = mb_info['ddr']
            rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            ram_names = [r['display_name'] for r in rams]
            
            curr_ram_idx = 0
            if conf['ram'] and conf['ram']['display_name'] in ram_names:
                curr_ram_idx = ram_names.index(conf['ram']['display_name'])
            else:
                curr_ram_idx = 0
            
            if ram_names:
                sel_ram_name = st.selectbox(f"选择内存 (规格: {ddr_type})", ram_names, index=curr_ram_idx)
                conf['ram'] = rams[ram_names.index(sel_ram_name)]
            else:
                st.warning(f"缺少 {ddr_type} 规格的内存数据")
                conf['ram'] = None
        else:
            conf['ram'] = None

        # --- 存储选择 ---
        ssds = data['storage']['storage_devices']
        ssd_names = [s['display_name'] for s in ssds]
        curr_ssd_idx = ssd_names.index(conf['ssd']['display_name']) if conf['ssd'] and conf['ssd']['display_name'] in ssd_names else 0
        sel_ssd_name = st.selectbox("选择固态硬盘 (SSD)", ssd_names, index=curr_ssd_idx)
        conf['ssd'] = ssds[ssd_names.index(sel_ssd_name)]

    # 3. 结果汇总区
    with col2:
        st.subheader("📋 配置清单汇总")
        conf = st.session_state.config
        
        # 基础校验：必须选择了 CPU 和 主板 才能计算
        if not conf['cpu'] or not conf['mb']:
            st.info("请在左侧完成核心配件选择以查看清单。")
        else:
            # --- 1. 价格计算逻辑 ---
            p_cpu = conf['cpu'].get('tray_price') or conf['cpu'].get('boxed_price', 0)
            p_gpu = conf['gpu']['price'] if conf['gpu'] else 0
            p_mb = conf['mb']['price'] if conf['mb'] else 0
            p_ram = conf['ram']['price'] if conf['ram'] else 0
            p_ssd = conf['ssd']['price'] if conf['ssd'] else 0
            
            total = p_cpu + p_gpu + p_mb + p_ram + p_ssd
            st.metric("总价估计", f"¥{total:,.2f}")
            
            # --- 2. 展示清单表格 ---
            summary_data = [
                ["处理器 (CPU)", conf['cpu']['model'], f"¥{p_cpu}"],
                ["显卡 (GPU)", conf['gpu']['model'] if conf['gpu'] else "集成显卡", f"¥{p_gpu}"],
                ["主板 (MB)", conf['mb']['model'], f"¥{p_mb}"],
                ["内存 (RAM)", conf['ram']['display_name'] if conf['ram'] else "未选择", f"¥{p_ram}"],
                ["硬盘 (SSD)", conf['ssd']['display_name'] if conf['ssd'] else "未选择", f"¥{p_ssd}"]
            ]
            st.table(summary_data)

            # --- 3. 专家评估按钮逻辑 ---
            st.write("---")
            # 专家评估现在是点击触发
            if st.button("🔍 执行专家评估报告", use_container_width=True):
                with st.status("正在分析硬件匹配度...", expanded=True) as status:
                    has_issue = False
                    
                    # A. 场景校验：生产力
                    if req == "生产力":
                        if conf['ram'] and conf['ram'].get('capacity', 0) < 32:
                            st.warning("【内存评估】生产力场景建议 32G 以上内存，当前配置可能在多任务处理时遇到瓶颈。")
                            has_issue = True
                        if conf['gpu']:
                            try:
                                # 健壮的数字提取：从 "12GB GDDR6" 提取 12
                                vram_val = int(''.join(filter(str.isdigit, conf['gpu']['vram'])))
                                if vram_val < 12:
                                    st.info("【显存建议】深度学习、复杂渲染或 AI 计算建议选择 12G 以上显存的型号。")
                                    has_issue = True
                            except: pass

                    # B. 场景校验：游戏
                    elif req == "游戏":
                        # 检查“头重脚轻”配置：高等级CPU配入门显卡
                        if conf['cpu'].get('tier') == "high":
                            if not conf['gpu'] or conf['gpu'].get('tier') == "entry":
                                st.error("【平衡性警告】配置『头重脚轻』。顶级 CPU 搭配入门显卡会产生严重的图形瓶颈，无法发挥性能。")
                                has_issue = True

                    # C. 兼容性红线：无核显且未选独显
                    if not conf['cpu'].get('igpu', True) and not conf['gpu']:
                        st.error("【致命错误】当前 CPU 无内置核显，且未安装独立显卡。系统将无法点亮画面！")
                        has_issue = True
                    
                    # D. 完美配置反馈
                    if not has_issue:
                        st.success("【评估完成】当前配置在当前场景下平衡性良好，未发现明显缺陷！")
                    # 专家评估补充逻辑
                    # 专家评估补充逻辑
                    # 1. 显卡高过 CPU 检测
                    tier_weights = {"entry": 1, "mid": 2, "high": 3}
                    cpu_weight = tier_weights.get(conf['cpu'].get('tier'), 0)
                    gpu_weight = tier_weights.get(conf['gpu'].get('tier'), 0) if conf['gpu'] else 0
                    
                    if gpu_weight > cpu_weight:
                        st.warning("【瓶颈预警】显卡等级高于 CPU。在某些 CPU 密集型游戏或任务中，显卡性能可能无法完全释放。")
                        has_issue = True
                
                    # 2. 8GB 内存检测
                    if conf['ram'] and conf['ram'].get('capacity', 0) <= 8:
                        if req == "游戏" or req == "生产力":
                            st.error("【内存严重不足】8GB 内存无法满足现代游戏/生产力需求，建议至少升级至 16GB。")
                            has_issue = True
                    
                    status.update(label="评估分析完成", state="complete", expanded=True)

if __name__ == "__main__":
    main()
