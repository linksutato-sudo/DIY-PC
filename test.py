import streamlit as st
import json
import os

st.set_page_config(page_title="DIY PC 专家助手", layout="wide", page_icon="💻")

# ================= 数据加载 =================
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
            st.error(f"{filename} 加载失败: {e}")
            data[key] = {}
    return data


# ================= 安全工具函数 =================
def safe_next(iterable):
    return next(iter(iterable), None)


def get_price(item):
    if not item:
        return 0
    return item.get('price') or item.get('tray_price') or item.get('boxed_price') or 0


# ================= 推荐算法（强化版） =================
def get_auto_recommendation(budget, requirement, data):
    STRATEGY_MAP = {
        "办公": {"tiers": ["low", "entry"], "cpu_ratio": 0.4, "gpu_ratio": 0.0, "tag": "office"},
        "网游/影音": {"tiers": ["entry", "mid"], "cpu_ratio": 0.35, "gpu_ratio": 0.35, "tag": "gaming"},
        "主流3A/剪辑": {"tiers": ["mid", "high-mid"], "cpu_ratio": 0.3, "gpu_ratio": 0.45, "tag": "gaming"},
        "4K游戏/直播": {"tiers": ["high-mid", "top"], "cpu_ratio": 0.25, "gpu_ratio": 0.55, "tag": "gaming"},
        "旗舰/渲染/AI": {"tiers": ["top"], "cpu_ratio": 0.4, "gpu_ratio": 0.4, "tag": "production"}
    }

    strat = STRATEGY_MAP[requirement]

    all_cpus = data['cpus'].get('Intel_Processors', []) + data['cpus'].get('AMD_Processors', [])
    cpus = [c for c in all_cpus if c['tier'] in strat['tiers']]

    cpus.sort(key=get_price, reverse=True)

    for cpu in cpus:
        cpu_price = get_price(cpu)
        if cpu_price > budget * (strat['cpu_ratio'] + 0.2):
            continue

        # GPU
        need_gpu = not (requirement == "办公" and cpu.get('igpu', True))
        gpu = None

        if need_gpu:
            gpus = data['gpus'].get('gpus', [])
            valid_gpus = [g for g in gpus if get_price(g) <= budget * (strat['gpu_ratio'] + 0.2)]

            if not valid_gpus:
                continue

            valid_gpus.sort(key=lambda x: (get_price(x), int(x['vram'].replace("GB", ""))), reverse=True)
            gpu = valid_gpus[0]

        # 主板
        socket = cpu['socket']
        series_list = [s for s in data['mb_series'].get('Motherboard_Series', []) if s['socket'] == socket]

        if not series_list:
            continue

        series_names = [s['series'] for s in series_list]

        mbs = [m for m in data['mb_models'].get('motherboard_models', []) if m['series'] in series_names]
        if not mbs:
            continue

        mbs.sort(key=get_price)
        mb = mbs[0]

        # 主板信息
        mb_info = safe_next(s for s in series_list if s['series'] == mb['series'])

        # 内存
        ram = None
        if mb_info:
            ram = safe_next(r for r in data['memory'].get('memory_modules', []) if r['type'] == mb_info['ddr'])

        # SSD
        ssd = safe_next(s for s in data['storage'].get('storage_devices', []) if strat['tag'] in s.get('usage', []))
        if not ssd:
            ssd = safe_next(data['storage'].get('storage_devices', []))

        total = sum([
            get_price(cpu),
            get_price(gpu),
            get_price(mb),
            get_price(ram),
            get_price(ssd)
        ])

        if total <= budget * 1.15:
            return {"cpu": cpu, "gpu": gpu, "mb": mb, "ram": ram, "ssd": ssd, "total": total}

    return None


# ================= 主程序 =================
def main():
    data = load_all_data()
    all_cpus = data['cpus'].get('Intel_Processors', []) + data['cpus'].get('AMD_Processors', [])

    if 'config' not in st.session_state:
        st.session_state.config = {
            "cpu": all_cpus[0] if all_cpus else None,
            "gpu": None,
            "mb": None,
            "ram": None,
            "ssd": safe_next(data['storage'].get('storage_devices', []))
        }

    # ===== Sidebar =====
    with st.sidebar:
        st.header("⚙️ 智能配置")
        budget = st.number_input("预算", 2000, 100000, 6000, step=500)
        req = st.selectbox("用途", ["办公", "网游/影音", "主流3A/剪辑", "4K游戏/直播", "旗舰/渲染/AI"])

        if st.button("✨ 自动推荐"):
            res = get_auto_recommendation(budget, req, data)
            if res:
                st.session_state.config = res
                st.success("推荐完成")
            else:
                st.error("预算不足或数据缺失")

    conf = st.session_state.config

    # ===== CPU =====
    cpu_names = [c['model'] for c in all_cpus]
    cpu_idx = cpu_names.index(conf['cpu']['model']) if conf['cpu'] else 0

    sel_cpu = st.selectbox("CPU", cpu_names, index=cpu_idx)
    new_cpu = safe_next(c for c in all_cpus if c['model'] == sel_cpu)

    if new_cpu != conf['cpu']:
        conf['cpu'] = new_cpu
        conf['mb'] = None
        conf['ram'] = None

    # ===== GPU =====
    gpus = data['gpus'].get('gpus', [])
    gpu_list = ["不选"] + [f"{g['brand']} {g['model']}" for g in gpus]

    sel_gpu = st.selectbox("GPU", gpu_list)
    conf['gpu'] = None if sel_gpu == "不选" else gpus[gpu_list.index(sel_gpu)-1]

    # ===== 主板 =====
    if conf['cpu']:
        socket = conf['cpu']['socket']

        series = [s for s in data['mb_series'].get('Motherboard_Series', []) if s['socket'] == socket]
        mbs = [m for m in data['mb_models'].get('motherboard_models', []) if m['series'] in [s['series'] for s in series]]

        if mbs:
            mb_names = [f"{m['brand']} {m['model']}" for m in mbs]
            sel_mb = st.selectbox("主板", mb_names)
            conf['mb'] = mbs[mb_names.index(sel_mb)]

    # ===== 内存 =====
    if conf['mb']:
        mb_info = safe_next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == conf['mb']['series'])

        if mb_info:
            rams = [r for r in data['memory']['memory_modules'] if r['type'] == mb_info['ddr']]
            if rams:
                ram_names = [r['display_name'] for r in rams]
                sel_ram = st.selectbox("内存", ram_names)
                conf['ram'] = rams[ram_names.index(sel_ram)]

    # ===== SSD =====
    ssds = data['storage'].get('storage_devices', [])
    ssd_names = [s['display_name'] for s in ssds]
    sel_ssd = st.selectbox("SSD", ssd_names)
    conf['ssd'] = ssds[ssd_names.index(sel_ssd)]

    # ===== 汇总 =====
    total = sum([
        get_price(conf['cpu']),
        get_price(conf['gpu']),
        get_price(conf['mb']),
        get_price(conf['ram']),
        get_price(conf['ssd'])
    ])

    st.metric("总价", f"¥{total}")

    st.json(conf)


if __name__ == "__main__":
    main()
