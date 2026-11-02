"""Opt-in synthetic notes; seed only an entirely empty demonstration library."""


def seed_galaxy_demo(store):
    if store.stats()["active"] or store.stats()["trash"]:
        return
    clusters = {
        "设计灵感": [
            "让知识，连接成宇宙",
            "留白是一种表达",
            "色彩与情绪的关系",
            "交互设计的四个细节",
            "建立自己的灵感收集箱",
            "好的设计让选择更简单",
        ],
        "前端开发": [
            "React：从组件开始",
            "用状态描述界面",
            "CSS布局的空间感",
            "动画应该传达什么",
            "理解浏览器的渲染",
            "Three.js与三维空间",
        ],
        "算法笔记": [
            "动态规划的思考方式",
            "图：关系的另一种语言",
            "从递归到记忆化",
            "搜索与路径的选择",
            "拆解一个复杂问题",
            "为什么需要边界条件",
        ],
        "读书摘录": [
            "把书读成自己的问题",
            "深度工作的节奏",
            "记录比记住更可靠",
            "重新理解长期主义",
            "连接不同领域的想法",
            "一本书的三个收获",
        ],
        "学习复盘": [
            "本周，有哪些新的连接",
            "把目标拆成小行动",
            "复习不是重复阅读",
            "在输出中发现盲点",
            "让学习形成闭环",
            "下一步，保持好奇",
        ],
    }
    notes = []
    for group, titles in clusters.items():
        for index, title in enumerate(titles):
            body = (
                f"# {title}\n\n每一个想法都不是孤岛。把它记下来，再看看它与哪些知识有关。\n\n"
                f"## 关于{group}\n\n"
                "比起收集更多信息，更重要的是建立可以反复使用的理解。给一个概念写下例子、边界和自己的疑问，"
                "下次遇到类似问题时，就有了一条回到它的路。\n\n"
                "## 可以尝试的小行动\n\n- 用一句话概括今天的收获\n- 找到一个相关的想法并建立关联\n- 留下一个值得继续探索的问题\n\n"
                "> 知识的价值，常常发生在连接的瞬间。\n\n"
                "**我的思考**：这条笔记可以继续编辑，所有修改都会保存在本机。"
            )
            notes.append(
                store.create(
                    title, body, [group, "灵感" if index % 3 == 0 else "知识积累"]
                )
            )
    for i, note in enumerate(notes):
        targets = [notes[(i // 6) * 6 + (i + 1) % 6], notes[(i + 7) % len(notes)]]
        body = (
            note.body
            + "\n\n## 关联阅读\n\n"
            + "\n\n".join(f"[[note:{target.id}]]" for target in targets)
        )
        store.save(note.id, note.title, body, note.tags, note.revision)
    old = store.create(
        "一闪而过的想法",
        "# 灵感也有第二次机会\n\n从回收站恢复，关联与身份仍然保留。",
        ["设计灵感"],
    )
    store.set_deleted(old.id, True)
