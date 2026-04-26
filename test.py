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

        # 5. 匹配内存 (根据主板 DDR 类型)
        mb_info = next(s for s in valid_series if s['series'] == mb['series'])
        ddr_type = mb_info['ddr']
        potential_rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
        
        # --- 核心区别：内存筛选 ---
        if requirement == "生产力":
            # 生产力优先选容量大的（32G及以上）
            potential_rams.sort(key=lambda x: x.get('capacity', 0), reverse=True)
        else:
            # 游戏和办公选最实惠的
            potential_rams.sort(key=lambda x: x['price'])

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

    with col1:
        st.subheader("🛠️ 配件手工微调")
        conf = st.session_state.config

        # --- CPU 选择 ---
        all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
        cpu_names = [c['model'] for c in all_cpus]
        curr_cpu_idx = cpu_names.index(conf['cpu']['model']) if conf['cpu'] else 0
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
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        mb_names = [f"{m['brand']} {m['model']}" for m in mbs]
        
        curr_mb_idx = 0
        if conf['mb']:
            target_mb_name = f"{conf['mb']['brand']} {conf['mb']['model']}"
            if target_mb_name in mb_names:
                curr_mb_idx = mb_names.index(target_mb_name)
        # 如果当前主板不兼容新选的CPU，强制重置为兼容列表第一个
        elif mb_names:
            curr_mb_idx = 0

        if mb_names:
            sel_mb_name = st.selectbox(f"选择主板 (接口: {socket})", mb_names, index=curr_mb_idx)
            conf['mb'] = mbs[mb_names.index(sel_mb_name)]
        else:
            st.error(f"警告：库中没有支持 {socket} 的主板！")
            conf['mb'] = None

        # --- 内存选择 (基于主板 DDR 类型联动) ---
        if conf['mb']:
            mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])
            ddr_type = mb_info['ddr']
            rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            ram_names = [r['display_name'] for r in rams]
            
            curr_ram_idx = 0
            if conf['ram'] and conf['ram']['display_name'] in ram_names:
                curr_ram_idx = ram_names.index(conf['ram']['display_name'])
            
            sel_ram_name = st.selectbox(f"选择内存 (规格: {ddr_type})", ram_names, index=curr_ram_idx)
            conf['ram'] = rams[ram_names.index(sel_ram_name)]
        else:
            conf['ram'] = None

        # --- 存储选择 ---
        ssds = data['storage']['storage_devices']
        ssd_names = [s['display_name'] for s in ssds]
        curr_ssd_idx = ssd_names.index(conf['ssd']['display_name']) if conf['ssd'] else 0
        sel_ssd_name = st.selectbox("选择固态硬盘 (SSD)", ssd_names, index=curr_ssd_idx)
        conf['ssd'] = ssds[ssd_names.index(sel_ssd_name)]

    # 3. 结果汇总区
    with col2:
        st.subheader("📋 配置清单汇总")
        # 直接使用已更新的 conf
        if not conf['cpu'] or not conf['mb']:
            st.info("请完成核心配件选择")
        else:
            p_cpu = conf['cpu'].get('tray_price') or conf['cpu'].get('boxed_price', 0)
            p_gpu = conf['gpu']['price'] if conf['gpu'] else 0
            p_mb = conf['mb']['price'] if conf['mb'] else 0
            p_ram = conf['ram']['price'] if conf['ram'] else 0
            p_ssd = conf['ssd']['price'] if conf['ssd'] else 0
            
            total = p_cpu + p_gpu + p_mb + p_ram + p_ssd
            st.metric("总价估计", f"¥{total:,.2f}")
            
            summary_data = [
                ["处理器", conf['cpu']['model'], f"¥{p_cpu}"],
                ["显卡", conf['gpu']['model'] if conf['gpu'] else "集成显卡", f"¥{p_gpu}"],
                ["主板", conf['mb']['model'], f"¥{p_mb}"],
                ["内存", conf['ram']['display_name'] if conf['ram'] else "未选择", f"¥{p_ram}"],
                ["硬盘", conf['ssd']['display_name'] if conf['ssd'] else "未选择", f"¥{p_ssd}"]
            ]
            st.table(summary_data)

            st.subheader("💡 专家评估")
            # 这里的 req 来自侧边栏 selectbox
            if req == "生产力":
                if conf['ram'] and conf['ram'].get('capacity', 0) < 32:
                    st.warning("建议：生产力场景建议 32G 以上内存。")
                if conf['gpu']:
                    try:
                        vram_val = int(''.join(filter(str.isdigit, conf['gpu']['vram'])))
                        if vram_val < 12:
                            st.info("提示：复杂渲染建议 12G 以上显存。")
                    except: pass

            if req == "游戏":
                if conf['cpu'].get('tier') == "high" and (not conf['gpu'] or conf['gpu'].get('tier') == "entry"):
                    st.error("警告：配置『头重脚轻』，CPU过强而显卡过弱。")

            if not conf['cpu'].get('igpu', True) and not conf['gpu']:
                st.error("⚠️ 致命错误：该CPU无核显且未选独显，无法开机！")

if __name__ == "__main__":
    main()
