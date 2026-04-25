import re

# -----------------------------
# 规则常量（后面可以扩展成 JSON）
# -----------------------------
DDR4_KEYWORDS = ["D4", "DDR4"]

DDR5_CHIPSETS = ["Z790", "Z890", "X870", "B850", "B760"]

PCIe5_FULL = ["Z790", "Z890", "X870"]

PCIe5_PARTIAL = ["B760", "B850"]


def add_tags_to_motherboards(data):
    for board in data["motherboard_models"]:
        model = board["model"].upper()
        series = board["series"].upper()

        tags = set()

        # =========================
        # 1. 功能类
        # =========================

        # WIFI / BT
        if "WIFI" in model or "WIRELESS" in model:
            tags.add("WIFI")
            tags.add("BT")

        # DDR4 / DDR5（修复：不再用数字猜）
        if any(k in model for k in DDR4_KEYWORDS):
            tags.add("DDR4")
        elif any(c in series for c in DDR5_CHIPSETS):
            tags.add("DDR5")

        # PCIe 5.0
        if any(x in series for x in PCIe5_FULL):
            tags.add("PCIe5")
        elif any(x in series for x in PCIe5_PARTIAL) and any(
            k in model for k in ["STRIX", "TUF"]
        ):
            tags.add("PCIe5")

        # =========================
        # 2. 定位类（全部独立 if，不用 elif）
        # =========================

        if any(x in model for x in ["EXTREME", "HERO", "APEX"]):
            tags.add("High-End")

        if "PROART" in model:
            tags.add("Pro/Creator")

        if any(x in model for x in ["STRIX", "TUF", "TX GAMING"]):
            tags.add("Gaming")

        if "PRIME" in model:
            if any(x in model for x in ["-PLUS", "-P"]):
                tags.add("Value")
            elif any(x in model for x in ["-K", "-R", "-F", "-E", "AYW"]):
                tags.add("Budget")
            else:
                tags.add("Value")

        if series.startswith("H"):
            tags.add("Budget")

        # =========================
        # 3. 设计类
        # =========================

        if any(x in model for x in ["WHITE", "吹雪", "SNOW"]):
            tags.add("White")

        # RGB（更保守）
        if "STRIX" in model or "TX GAMING" in model:
            tags.add("RGB")
        elif "TUF" in model and "PLUS" in model:
            tags.add("RGB")

        # =========================
        # 输出
        # =========================
        board["tags"] = sorted(tags)

    return data
