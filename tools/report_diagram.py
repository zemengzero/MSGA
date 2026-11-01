from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_architecture(root):
    out = Path(root) / "docs/images"
    out.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (1400, 720), "white")
    d = ImageDraw.Draw(im)

    def text(x, y, s, size=28):
        d.text(
            (x, y),
            s,
            font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", size),
            fill="#17324d",
        )

    def box(x, y, w, h, title, desc):
        d.rounded_rectangle(
            (x, y, x + w, y + h), radius=16, fill="#eef3fb", outline="#9db4d1", width=3
        )
        text(x + 20, y + 20, title, 31)
        for i, line in enumerate(desc):
            text(x + 20, y + 70 + i * 37, line, 25)

    def arrow(a, b):
        d.line([a, b], fill="#5378a5", width=4)
        x, y = b
        d.polygon([(x, y), (x - 9, y - 17), (x + 9, y - 17)], fill="#5378a5")

    box(
        450,
        35,
        510,
        140,
        "桌面界面  Tkinter/ttk",
        ["ui.py / __main__.py", "事件、阅读、状态、未保存守卫"],
    )
    box(
        30,
        270,
        390,
        150,
        "搜索与关联",
        ["search.py / links.py", "AND筛选、稳定UUID、反向引用"],
    )
    box(
        500,
        270,
        390,
        150,
        "笔记业务与事务",
        ["store.py / models.py", "校验、写锁、revision、历史"],
    )
    box(
        970,
        270,
        400,
        150,
        "迁移与保护",
        ["transfer.py / backup.py", "安全导出、快照、保护恢复"],
    )
    for x in [225, 695, 1170]:
        arrow((705, 175), (x, 270))
    box(
        350,
        550,
        700,
        125,
        "SQLite：唯一权威数据源",
        ["notes / tags / note_tags / links / history / settings"],
    )
    for x in [225, 695, 1170]:
        arrow((x, 420), (700, 550))
    im.save(out / "architecture.png")
    return out / "architecture.png"
