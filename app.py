import streamlit as st
import json
import os

# 配置页面
st.set_page_config(page_title="DIY PC 配件助手", layout="wide")

# 加载数据函数
@st.cache_data
def load_all_data():
    base_path = "/data"
    data = {}
    files = {
        "cpus": "cpus.json",
        "memory": "memory_modules.json",
        "mb_models": "motherboard_models.json",
        "mb_series": "motherboards_series.json",
        "storage": "storage_devices.json"
    }
    for key, filename in files.items():
        with open(os.path.join(base_path, filename), 'r', encoding='utf-8') as f:
            data[key] = json.load(f)
    return data

def get_recommendation(budget, requirement, data):
    # 1. 需求与等级映射
    tier_map = {
        "办公": ["entry", "mid"],
        "游戏": ["mid", "high"],
        "生产力": ["high"]
    }
    target_tiers = tier_map.get(requirement, ["mid"])
    usage_tag = "office" if requirement == "办公" else ("gaming" if requirement == "游戏" else "production")

    # 合并 Intel 和 AMD CPU
    all_cpus = data['cpus']['Intel_Processors'] + data['cpus']['AMD_Processors']
    
    # 筛选 CPU：符合等级且价格在总预算的 40% 以内
    potential_cpus = [c for c in all_cpus if c['tier'] in target_tiers and (c.get('tray_price') or c.get('boxed_price', 0)) <= budget * 0.4]
    potential_cpus.sort(key=lambda x: x.get('tray_price') or x.get('boxed_price', 0), reverse=True)

    recommendations = []

    for cpu in potential_cpus[:5]: # 尝试前 5 个最强 CPU
        cpu_price = cpu.get('tray_price') or cpu.get('boxed_price', 0)
        socket = cpu['socket']
        
        # 2. 匹配主板系列（基于 Socket）
        valid_series = [s for s in data['mb_series']['Motherboard_Series'] if s['socket'] == socket]
        series_names = [s['series'] for s in valid_series]
        
        # 3. 匹配具体主板型号
        potential_mbs = [m for m in data['mb_models']['motherboard_models'] if m['series'] in series_names]
        potential_mbs.sort(key=lambda x: x['price'])

        for mb in potential_mbs:
            # 获取主板对应的 DDR 类型
            mb_info = next(s for s in valid_series if s['series'] == mb['series'])
            ddr_type = mb_info['ddr']
            
            # 4. 匹配内存 (DDR 类型一致)
            potential_rams = [r for r in data['memory']['memory_modules'] if r['type'] == ddr_type]
            potential_rams.sort(key=lambda x: x['price'])
            
            # 5. 匹配存储 (包含对应 usage 标签)
            potential_ssds = [s for s in data['storage']['storage_devices'] if usage_tag in s['usage']]
            potential_ssds.sort(key=lambda x: x['price'])

            if potential_rams and potential_ssds:
                best_ram = potential_rams[0]
                best_ssd = potential_ssds[0]
                total = cpu_price + mb['price'] + best_ram['price'] + best_ssd['price']
                
                if total <= budget:
                    return {
                        "cpu": cpu,
                        "motherboard": mb,
                        "ram": best_ram,
                        "storage": best_ssd,
                        "total": total,
                        "reason": f"在 {budget} 元预算下，选择了支持 {socket} 接口的 {cpu['model']}，"
                                  f"配合 {mb['brand']} {mb['model']} 主板。内存选用了兼容的 {best_ram['type']} "
                                  f"规格，存储则选用了针对 {requirement} 场景优化的 {best_ssd['brand']} 固态硬盘。"
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
                st.write(f"**主板:** {result['motherboard']['brand']} {result['motherboard']['model']}")
                st.write(f"**内存:** {result['ram']['display_name']}")
                st.write(f"**存储:** {result['storage']['display_name']}")
            
            with col2:
                st.subheader("💡 推荐理由")
                st.write(result['reason'])
                
            # 详细数据展示
            with st.expander("查看配件详细参数"):
                st.json(result)
        else:
            st.error("抱歉，在当前预算和需求下未找到匹配的组合，请尝试提高预算。")

if __name__ == "__main__":
    main()
