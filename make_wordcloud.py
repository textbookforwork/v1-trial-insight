# -*- coding: utf-8 -*-
"""產生「老師」「學生」兩張正面回饋散落式文字雲 PNG。"""
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\msjhbd.ttc"   # 微軟正黑體 Bold
FONT_PATH_FALLBACK = r"C:\Windows\Fonts\msjh.ttc"
import os
if not os.path.exists(FONT_PATH):
    FONT_PATH = FONT_PATH_FALLBACK

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

teacher_quotes = [
    "可以自己編排順序，依教學流程走，不用一直跳來跳去",
    "順暢、不被綁在框架的教科書上，這是我最喜歡的改變",
    "老師可以自行編輯，放入自己的教學脈絡",
    "數位教育最好的就是讓雜訊變更少，一次只看一段重點",
    "編排邏輯符合教學，我可以準確提問，學生跟得上",
    "在操作的過程中，學生自然而然就接受了邊角邊（SAS）",
    "小細胞像一對一的自主學習教練",
    "截圖功能很棒，把問題鎖定在課本裡，有利學生聚焦",
    "自由書寫、自由學習，能滿足差異化教學",
    "幫了很多特教生，不會意識到在被評量，容易做多元評量",
    "系統讓大家很專注，參與度高、踴躍發言",
    "同樣的事做不膩，因為有一個好目標",
    "多一個東西給孩子學習，其實是好事",
]

student_quotes = [
    "前面可以個性化題目，依自己的狀況出題",
    "可以互動、可以學習，還可以自行操作",
    "我喜歡操作，當成遊戲很好玩",
    "用完之後會幫你檢討，拆解成很多步驟再合併，比直接給答案更好",
    "探索星球答對了，讓我蠻有成就感",
    "邊玩遊戲、邊畫重點、邊複習",
    "這堂課讓我大開眼界，可以在題目裡畫重點，也能玩遊戲",
    "這次的 AI 聚焦在範圍裡，用比較好懂的方式幫我們了解概念",
    "不用一直盯著無聊的課文，上課變比較有趣",
    "學完之後可以馬上測驗，練習個幾題",
    "用線上直接看到課本，不用帶那麼多本書",
    "出國也能用拍照學英語",
]

# 配色
teacher_colors = ["#1f6f78", "#2a9d8f", "#0b5d69", "#3a7ca5", "#16697a",
                  "#287271", "#1d617a", "#2c6e7f", "#0e7c86"]
student_colors = ["#e76f51", "#e9844a", "#f4a261", "#d65a8a", "#c8553d",
                  "#e07a5f", "#bc4b6b", "#ef8354", "#d1495b"]


def wrap(s, limit=15):
    """過長句子在逗號附近折成兩行。"""
    if len(s) <= limit:
        return s
    seps = [i for i, ch in enumerate(s) if ch in "，、（"]
    if not seps:
        mid = len(s) // 2
        return s[:mid] + "\n" + s[mid:]
    mid = len(s) / 2
    best = min(seps, key=lambda i: abs(i - mid))
    # 在逗號後折行（逗號留在上一行）
    if s[best] == "，" or s[best] == "、":
        return s[:best + 1] + "\n" + s[best + 1:]
    return s[:best] + "\n" + s[best:]


def fontsize_for(raw_len, fs_min=23, fs_max=46):
    size = fs_max - (raw_len - 6) * 1.15
    return max(fs_min, min(fs_max, size))


def build(quotes, colors, title, out_name, seed):
    rng = random.Random(seed)
    W, H = 1920, 1200
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("#fbfaf7")
    ax.set_facecolor("#fbfaf7")

    # 標題
    fp_title = FontProperties(fname=FONT_PATH, size=52)
    ax.text(0.5, 0.955, title, ha="center", va="center",
            fontproperties=fp_title, color="#222222")
    ax.plot([0.30, 0.70], [0.905, 0.905], color=colors[0], lw=3, alpha=0.6)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    placed = []  # 已放置的 bbox (x0,y0,x1,y1) display px
    pad = 10

    def overlaps(bb):
        for (a0, b0, a1, b1) in placed:
            if not (bb.x1 + pad < a0 or bb.x0 - pad > a1 or
                    bb.y1 + pad < b0 or bb.y0 - pad > b1):
                return True
        return False

    items = sorted(quotes, key=len, reverse=True)
    rotations_pool = [0, 0, 0, 0, -6, 6, -4, 4]

    for idx, q in enumerate(items):
        raw_len = len(q)
        fs = fontsize_for(raw_len)
        text = wrap(q, limit=16)
        color = colors[idx % len(colors)]
        rot = rng.choice(rotations_pool)
        fp = FontProperties(fname=FONT_PATH, size=fs)
        placed_ok = False
        attempts = 0
        cur_fs = fs
        while not placed_ok and cur_fs >= 17:
            fp = FontProperties(fname=FONT_PATH, size=cur_fs)
            for _ in range(900):
                attempts += 1
                x = rng.uniform(0.05, 0.95)
                y = rng.uniform(0.07, 0.87)
                t = ax.text(x, y, text, ha="center", va="center",
                            fontproperties=fp, color=color, rotation=rot,
                            linespacing=1.05)
                bb = t.get_window_extent(renderer=renderer)
                # 邊界檢查
                if bb.x0 < 12 or bb.x1 > W - 12 or bb.y0 < 12 or bb.y1 > H * 0.90:
                    t.remove()
                    continue
                if overlaps(bb):
                    t.remove()
                    continue
                placed.append((bb.x0, bb.y0, bb.x1, bb.y1))
                placed_ok = True
                break
            if not placed_ok:
                cur_fs -= 2
        if not placed_ok:
            print("WARN 無法放置:", q)

    out_path = os.path.join(OUT_DIR, out_name)
    fig.savefig(out_path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    print("已輸出:", out_path)


if __name__ == "__main__":
    build(teacher_quotes, teacher_colors,
          "老師的回饋", "正面回饋_老師.png", seed=7)
    build(student_quotes, student_colors,
          "學生的回饋", "正面回饋_學生.png", seed=23)
