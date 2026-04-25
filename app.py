import streamlit as st
import json
import os

st.set_page_config(page_title="DIY-PC 智能导购", page_icon="🖥️")

st.title("🖥️ DIY-PC 硬件导购系统")

# 稳妥的路径读取方式
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'data', 'cpus.json')

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    st.error("❌ 找不到数据库文件，请检查 data/cpus.json 是否已上传。")
    st.stop()

# 平台选择
brand = st.radio("选择平台", ["Intel", "AMD"], horizontal=True)

if brand == "Intel":
    cpus = data["Intel_Processors"]
else:
    cpus = data["AMD_Processors"]

# 型号选择
selected_model = st.selectbox("选择处理器型号", [c["model"] for c in cpus])

# 匹配选中的数据
selected_data = next((item for item in cpus if item["model"] == selected_model), None)

if selected_data:
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 处理器详情")
        st.write(f"**型号:** {selected_data['model']}")
        st.write(f"**核心规格:** {selected_data.get('specs', '暂无')}")
        
        # 价格展示
        if "tray_price" in selected_data and selected_data["tray_price"] != "缺货":
            st.metric("行情散片价", f"￥{selected_data['tray_price']}")
        if "boxed_price" in selected_data:
            st.metric("行情盒装价", f"￥{selected_data['boxed_price']}")

    with col2:
        st.subheader("🔌 兼容性与主板")
        
        # 获取主板信息逻辑
        mb_info = selected_data.get("supported_motherboards", "")
        
        # 如果 JSON 里没写（主要针对目前 AMD 部分），自动根据型号推断
        if not mb_info:
            if "5500" in selected_model or "5600" in selected_model or "5700" in selected_model:
                mb_info = "A520 / B550 / X570 (AM4接口)"
            elif "7000" in selected_model or "9000" in selected_model or "7800" in selected_model or "9800" in selected_model:
                mb_info = "B650 / X670 / B850 (AM5接口)"
            else:
                mb_info = "请咨询店员核对接口"

        st.success(f"**推荐搭配主板系列:** \n\n {mb_info}")
        
        # 额外提示
        if "15代" in selected_model:
            st.warning("⚠️ 注意：15代 Ultra 必须搭配新的 LGA1851 接口主板（如 Z890）。")
        elif "1151针" in selected_data.get('specs', ''):
            st.info("💡 提示：该平台较为经典，建议搭配 H110 或 B150 系列。")

else:
    st.warning("未找到该型号的详细信息。")

# 假设已经读取了两个json
# 1. 找到选中CPU的针脚(Socket)
# 2. 到 motherboards.json 过滤出相同 Socket 的 series

selected_mb = next((m for m in mb_data["Motherboard_Series"] if m["socket"] in selected_cpu_specs), None)

if selected_mb:
    st.subheader("💡 推荐主板搭配")
    st.write(f"推荐系列：{selected_mb['series']}")
    st.metric("参考行情价", f"￥{selected_mb['reference_price']}")
    st.caption(f"备注：{selected_mb['note']}")
