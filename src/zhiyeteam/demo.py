"""Synthetic walkthrough data, clearly separated from human feedback."""
def seed_demo(store):
    if store.stats()["active"] or store.stats()["trash"]:return
    intro=store.create("欢迎来到知页","# 把知识留在手边\n\n知页是一个离线学习知识库。你可以：\n\n- 用 Markdown 记录课程与项目\n- 用关键词和标签找回内容\n- 用稳定关联串起知识\n- 通过版本、回收站和备份找回数据\n\n**先试一下：**修改标题，按 Ctrl+S 保存，再打开历史版本。",["开始使用","演示"])
    algorithm=store.create("动态规划：从状态到转移","# 动态规划\n\n动态规划通常分为四步：\n\n1. 定义状态\n2. 确定状态转移\n3. 写出边界条件\n4. 选择计算顺序\n\n## 例子：爬楼梯\n\n```python\ndef climb(n):\n    a, b = 1, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```\n\n**复习问题：**为什么可以只保留两个状态？",["课程","算法"])
    design=store.create("项目设计：清楚的边界","# 项目设计\n\n界面只负责交互，业务模块校验规则，数据层在一个事务中保存笔记、标签和版本。\n\n> 如果写入失败，界面应保留未保存内容。\n\n## 设计取舍\n\n本地工具不依赖网络账号，先把记录、查找和恢复这条主路径做好。",["项目","软件工程"])
    review=store.create("本周学习复盘",f"# 本周复盘\n\n## 已完成\n\n- 学习状态转移与边界条件\n- 实践事务与版本回退\n\n## 关联知识\n\n算法笔记：[[note:{algorithm.id}]]\n\n工程笔记：[[note:{design.id}]]\n\n## 下次行动\n\n把一个课堂问题写成可验证的小例子。",["复盘","课程"])
    store.create("Markdown 格式速查","# Markdown 速查\n\n**粗体**强调重点，`代码`标出命令。\n\n- 无序列表\n- 便于拆解要点\n\n> 引用提示\n\n| 场景 | 做法 |\n| --- | --- |\n| 找笔记 | 关键词与标签 |\n| 关联知识 | 插入稳定链接 |\n| 防误删 | 回收站与备份 |\n\n完整表格样式可以通过 HTML 导出查看。",["开始使用","工具"])
    old=store.create("一条待恢复的灵感","# 临时灵感\n\n误删的内容会留在回收站，可以恢复。",["灵感"])
    store.set_deleted(old.id,True)
    changed=store.save(design.id,design.title,design.body+"\n\n## 现场验证\n\n将内容修改后保存，再回退到前一版本。",design.tags,design.revision)
    return intro
