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

# --- 核心推荐逻辑：直接按 Tier 生成全家桶 ---
def get_standard_tiers(data):
    """
    直接根据五大级别，从 JSON 数据中提取各级别最强/最匹配的硬件
    """
    TIER_DEFS = {
        "low": {
            "name": "点亮办公型", 
            "desc": "满足日常文档、网课、轻度办公",
            "min_ram": 8, "min_ssd": 512, "usage": "office"
        },
        "entry": {
            "name": "入门竞技型", 
            "desc": "英雄联盟、CS2、影音娱乐",
            "min_ram": 16, "min_ssd": 512, "usage": "gaming"
        },
        "mid": {
            "name": "中端全能型", 
            "desc": "主流 3A 游戏、视频剪辑、多任务",
            "min_ram": 32, "min_ssd": 1024, "usage": "gaming"
        },
        "high-mid": {
            "name": "高端极客型", 
            "desc": "4K 丝滑游戏、重度直播、生产力",
            "min_ram": 32, "min_ssd": 2048, "usage": "gaming"
        },
        "top": {
            "name": "旗舰巅峰型", 
            "desc": "深度学习、3D 渲染、极端发烧友",
            "min_ram": 64, "min_ssd": 2048, "usage": "production"
        }
    }

    results = {}
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']

    for t_key, info in TIER_DEFS.items():
        # 1. 选 CPU (选该级别内最贵的，代表该级别性能上限)
        potential_cpus = [c for c in all_cpus if c['tier'] == t_key]
        potential_cpus.sort(key=lambda x: x.get('tray_price', 0) or x.get('boxed_price', 0), reverse=True)
        cpu = potential_cpus[0] if potential_cpus else None

        # 2. 选 GPU
        gpu = None
        if t_key != "low":
            potential_gpus = [g for g in data['gpus']['gpus'] if g['tier'] == t_key]
            potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            gpu = potential_gpus[0] if potential_gpus else None

        # 3. 选主板 (选适配该 CPU Socket 的主流款)
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == cpu['socket']]
        mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        mbs.sort(key=lambda x: x['price'], reverse=True)
        # 选该系列的中端或高端款，避免入门板配旗舰U
        mb = mbs[0] if mbs else None

        # 4. 选内存 (满足最小容量)
        mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == mb['series'])
        rams = [r for r in data['memory']['memory_modules'] if r['type'] == mb_info['ddr'] and r.get('capacity', 0) >= info['min_ram']]
        rams.sort(key=lambda x: x['price'])
        ram = rams[0] if rams else None

        # 5. 选硬盘 (满足最小容量)
        ssds = [s for s in data['storage']['storage_devices'] if s.get('capacity_gb', 0) >= info['min_ssd']]
        ssds.sort(key=lambda x: x['price'])
        ssd = ssds[0] if ssds else None

        # 计算总价
        p_cpu = cpu.get('tray_price', 0) or cpu.get('boxed_price', 0) if cpu else 0
        total = p_cpu + (gpu['price'] if gpu else 0) + (mb['price'] if mb else 0) + (ram['price'] if ram else 0) + (ssd['price'] if ssd else 0)

        results[t_key] = {
            "info": info, "cpu": cpu, "gpu": gpu, "mb": mb, "ram": ram, "ssd": ssd, "total": total
        }
    return results

# --- 主界面逻辑 ---
def main():
    data = load_all_data() # 假设你已有 load_all_data 函数
    tier_configs = get_standard_tiers(data)

    st.title("🚀 五大档位专家推荐配置单")
    st.info("系统已自动匹配各层级最佳性能组合，您可以根据需求直接对比选择。")

    # 使用 tabs 切换不同级别
    tabs = st.tabs(["⚪ 点亮办公", "🔵 入门竞技", "🟢 中端全能", "🟡 高端极客", "🔴 旗舰巅峰"])
    
    tier_keys = ["low", "entry", "mid", "high-mid", "top"]
    
    for i, tab in enumerate(tabs):
        t_key = tier_keys[i]
        conf = tier_configs[t_key]
        
        with tab:
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.header(conf['info']['name'])
                st.write(f"🎯 **适用场景**：{conf['info']['desc']}")
                st.metric("预估总价", f"¥ {conf['total']:,.0f}")
                
                # 核心硬约束指标展示
                st.markdown(f"""
                - **内存下限**: {conf['info']['min_ram']}GB
                - **存储下限**: {conf['info']['min_ssd']}GB
                """)

            with c2:
                # 详细清单表格
                summary_data = [
                    {"配件": "处理器 (CPU)", "型号": conf['cpu']['model'], "价格": f"¥{conf['cpu'].get('tray_price', 0)}"},
                    {"配件": "显卡 (GPU)", "型号": conf['gpu']['model'] if conf['gpu'] else "核显 (无独立显卡)", "价格": f"¥{conf['gpu']['price'] if conf['gpu'] else 0}"},
                    {"配件": "主板 (MB)", "型号": conf['mb']['model'], "价格": f"¥{conf['mb']['price']}"},
                    {"配件": "内存 (RAM)", "型号": conf['ram']['display_name'], "价格": f"¥{conf['ram']['price']}"},
                    {"配件": "硬盘 (SSD)", "型号": conf['ssd']['display_name'], "价格": f"¥{conf['ssd']['price']}"},
                ]
                st.table(summary_data)
                
                if st.button(f"配置这套 {conf['info']['name']}", key=f"apply_{t_key}"):
                    st.session_state.config = {
                        "cpu": conf['cpu'], "gpu": conf['gpu'], "mb": conf['mb'], 
                        "ram": conf['ram'], "ssd": conf['ssd']
                    }
                    st.success("配置已加载到微调区域！")

    st.write("---")
    st.subheader("💡 为什么这么配？（兼容性说明）")
    st.caption("1. 所有方案均通过 Socket 校验（如 LGA1700 / AM5）。\n2. 内存 DDR 类型严格与主板匹配。\n3. 内存与硬盘容量严格遵守您设定的最低行业标准。")
