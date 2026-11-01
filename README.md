# 知页 · 本地学习知识库

用于软件工程团队验收的 Windows 桌面程序：记录 Markdown 笔记，按关键词和标签找回知识，用稳定 UUID 关联笔记，通过历史版本、回收站和完整备份保护内容。

团队版选择 Python + Tkinter + SQLite，以离线可运行、代码易讲解和四人可分工为首要目标。前两次实验的 .NET/Markdown 文件方案属于设计探索；本项目独立维护团队需求基线与实际实现说明。

## 开发运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m zhiyeteam --demo
```

正式运行不带 `--demo`，默认将数据库保存到当前用户的本地应用数据目录。演示模式使用独立数据库，不覆盖正式笔记。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 团队提交约定

当前账号建立的基线不替代四位成员的贡献。每位成员使用自己的 GitHub 账号，在功能分支上实际修改、运行测试并提交，PR 中写明功能、代码位置、验证结果和已知限制。分工及逐次提交安排见 `docs/团队分工与提交计划.md`。

报告只记录实际执行的测试和反馈。用户反馈待真人试用后填写，不能把合成演示数据当作调研。最终要求以老师最新课堂说明为准。
