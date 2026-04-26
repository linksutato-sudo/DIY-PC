import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 配件助手", layout="wide")

# 加载数据函数
@st.cache_data
def load_all_data():
    base_path = "data"
    data = {}
    files = {
        "cpus": "cpus.json",
        "memory": "memory_modules.json",
        "mb_models": "motherboard_models.json",
        "mb_series": "motherboards_series.json",
        "storage": "storage_devices.json",
        "gpus": "gpus.json"
    }
    for key, filename in files.items():
        with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
            data[key] = json.load(f)
    return data

def get_recommendation(budget, requirement, data):
    # 1. 需求与标签/等级映射
    tier_map = {
        "办公": ["entry", "mid"],
        "游戏": ["mid", "high"],
        "生产力": ["high"]
    }
    target_tiers = tier_map.get(requirement, ["mid"])
    usage_tag = "office" if requirement == "办公" else ("gaming" if requirement == "游戏" else "production")

    # 2. 筛选潜在 CPU
    # 限制 CPU 价格不宜超过总预算的 40%
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    potential_cpus = [c for c in all_cpus if c['tier'] in target_tiers and (c.get('tray_price') or c.get('boxed_price', 0)) <= budget * 0.4]
    potential_cpus.sort(key=lambda x: x.get('tray_price') or x.get('boxed_price', 0), reverse=True)

    for cpu in potential_cpus:
        cpu_price = cpu.get('tray_price') or cpu.get('boxed_price', 0)
        socket = cpu['socket']
        
        # 3. GPU 逻辑判定
        # 规则：若无核显 或 属于游戏/生产力需求，则必须配显卡
        need_gpu = not cpu.get('igpu', True) or requirement in ["游戏", "生产力"]
        gpu_to_use = None
        gpu_price = 0
        
        if need_gpu:
            # 筛选显卡：符合用途，且价格在合理区间（例如不超过预算的 50%）
            potential_gpus = [g for g in data['gpus']['gpus'] 
                             if usage_tag in g['usage'] and g['price'] <= budget * 0.5]
            if not potential_gpus:
                continue # 如果这款 CPU 必须配显卡但没钱买了，跳过该 CPU
            
            potential_gpus.sort(key=lambda x: x['price'], reverse=True)
            gpu_to_use = potential_gpus[0]
            gpu_price = gpu_to_use['price']

        # 4. 匹配主板 (根据 CPU Socket)
        valid_series = [s for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        series_names = [s['series'] for s in valid_series]
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in series_names]
        potential_mbs.sort(key=lambda x: x['price'])

        for mb in potential_mbs:
            # 5. 匹配内存 (DDR 类型一致)
            mb_info = next(s for s in valid_series if s['series'] == mb['series'])
            ddr_type = mb_info['ddr']
            potential_rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            potential_rams.sort(key=lambda x: x['price'])
            
            # 6. 匹配存储
            potential_ssds = [s for s in data['storage']['storage_devices'] if usage_tag in s['usage']]
            potential_ssds.sort(key=lambda x: x['price'])

            if potential_rams and potential_ssds:
                ram = potential_rams[0]
                ssd = potential_ssds[0]
                total = cpu_price + mb['price'] + ram['price'] + ssd['price'] + gpu_price
                
                # 7. 最终预算检查
                if total <= budget:
                    reason = f"在 {budget} 元预算下，我们优先保障了核心性能。选择了 {cpu['model']}。"
                    if gpu_to_use:
                        reason += f"为了满足{requirement}需求，搭配了 {gpu_to_use['brand']} {gpu_to_use['chipset']} 独显。"
                    else:
                        reason += "由于办公需求且 CPU 自带强力核显，为您节省了独立显卡的开支。"
                    
                    return {
                        "cpu": cpu,
                        "gpu": gpu_to_use,
                        "motherboard": mb,
                        "ram": ram,
                        "storage": ssd,
                        "total": total,
                        "reason": reason
                    }
    return None
    
# UI 界面
def main():
    st.title("💻 DIY PC 智能配置助手")
    st.info("基于本地库存库生成的实时推荐方案")

    data = load_all_data()

    # 侧边栏输入
    with st.sidebar:
        st.header("配置需求")
        budget = st.number_input("您的预算 (RMB)", min_value=1000, max_value=50000, value=5000, step=500)
        requirement = st.selectbox("使用场景", ["办公", "游戏", "生产力"])
        submit = st.button("生成推荐方案")

    if submit:
        result = get_recommendation(budget, requirement, data)
        
        if result:
            st.success(f"为您找到最佳方案！预估总价：¥{result['total']:.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 配置清单")
                st.write(f"**CPU:** {result['cpu']['model']} ({result['cpu']['specs']})")
                
                # GPU 动态显示判断
                if result.get('gpu'):
                    st.write(f"**显卡:** {result['gpu']['brand']} {result['gpu']['model']} ({result['gpu']['vram']})")
                else:
                    st.write(f"**显卡:** CPU 集成显卡 (核显)")
                
                st.write(f"**主板:** {result['motherboard']['brand']} {result['motherboard']['model']}")
                st.write(f"**内存:** {result['ram']['display_name']}")
                st.write(f"**存储:** {result['storage']['display_name']}")
            
            with col2:
                st.subheader("💡 推荐理由")
                st.write(result['reason'])
                
          
        else:
            st.error("抱歉，在当前预算和需求下未找到满足兼容性要求的组合，请尝试调整预算或需求。")

if __name__ == "__main__":
    main()
