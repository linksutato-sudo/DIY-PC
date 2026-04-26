import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 自选助手", layout="wide")

@st.cache_data
def load_all_data():
    base_path = "/data"
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

def main():
    st.title("🛠️ DIY PC 自选配置清单")
    data = load_all_data()
    
    # 初始化总价
    total_price = 0.0

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("请选择您的配件")
        
        # 1. 选择 CPU
        all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
        cpu_options = {c['model']: c for c in all_cpus}
        selected_cpu_name = st.selectbox("核心处理器 (CPU)", options=list(cpu_options.keys()))
        selected_cpu = cpu_options[selected_cpu_name]
        cpu_p = selected_cpu.get('tray_price') or selected_cpu.get('boxed_price', 0)
        total_price += cpu_p

        # 2. 选择 显卡 (GPU)
        # 增加一个“不使用独立显卡”的选项
        gpu_list = data['gpus']['gpus']
        gpu_options = {"使用集成显卡 (¥0)": None}
        gpu_options.update({f"{g['brand']} {g['model']} (¥{g['price']})": g for g in gpu_list})
        selected_gpu_key = st.selectbox("图形显卡 (GPU)", options=list(gpu_options.keys()))
        selected_gpu = gpu_options[selected_gpu_key]
        if selected_gpu:
            total_price += selected_gpu['price']

        # 3. 选择 主板 (基于 CPU Socket 过滤)
        socket = selected_cpu['socket']
        valid_series = [s['series'] for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        mb_list = [m for m in data['mb_models']['motherboard_models'] if m['series'] in valid_series]
        mb_options = {f"{m['brand']} {m['model']} (¥{m['price']})": m for m in mb_list}
        
        if not mb_options:
            st.warning(f"库中暂无支持 {socket} 接口的主板")
            selected_mb = None
        else:
            selected_mb_key = st.selectbox("主板 (Motherboard)", options=list(mb_options.keys()))
            selected_mb = mb_options[selected_mb_key]
            total_price += selected_mb['price']

        # 4. 选择 内存 (基于主板 DDR 类型过滤)
        if selected_mb:
            # 找到当前主板系列对应的 DDR 类型
            mb_info = next(s for s in data['mb_series']['Motherboard_Series'] if s['series'] == selected_mb['series'])
            ddr_type = mb_info['ddr']
            ram_list = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            ram_options = {f"{r['display_name']} (¥{r['price']})": r for r in ram_list}
            selected_ram_key = st.selectbox(f"内存 (RAM - {ddr_type})", options=list(ram_options.keys()))
            selected_ram = ram_options[selected_ram_key]
            total_price += selected_ram['price']
        else:
            st.write("请先选择兼容的主板")
            selected_ram = None

        # 5. 选择 存储 (SSD)
        storage_list = data['storage']['storage_devices']
        storage_options = {f"{s['display_name']} (¥{s['price']})": s for s in storage_list}
        selected_ssd_key = st.selectbox("固态硬盘 (Storage)", options=list(storage_options.keys()))
        selected_ssd = storage_options[selected_ssd_key]
        total_price += selected_ssd['price']

    # 右侧展示实时清单
    with col2:
        st.subheader("🛒 实时配置清单")
        st.metric("预算合计", f"¥{total_price:,.2f}")
        
        with st.container(border=True):
            st.write(f"**CPU:** {selected_cpu_name}")
            st.write(f"**GPU:** {selected_gpu_key.split(' (')[0]}")
            if selected_mb:
                st.write(f"**主板:** {selected_mb['model']}")
            if selected_ram:
                st.write(f"**内存:** {selected_ram['display_name']}")
            st.write(f"**硬盘:** {selected_ssd['display_name']}")

        if st.button("保存当前配置", use_container_width=True):
            st.balloons()
            st.success("配置已锁定，可以截图保存或下单！")

        # 自动校验：如果不带核显且没选显卡，发出警告
        if not selected_cpu.get('igpu', True) and selected_gpu is None:
            st.error("⚠️ 警告：该 CPU 不带核显，必须选择一块独立显卡才能开机！")

if __name__ == "__main__":
    main()
