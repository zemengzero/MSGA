# 知页 · 本地学习知识库

## 知识星图界面（A新增）

![知识星图实测](reports/A/galaxy-overview.png)

新增React/Three.js深色知识星图与Windows WebView2桌面入口，节点/连线读取同一SQLite库。新建、搜索、关联、自动保存、版本、回收站和备份导出均调用已有业务模块；原Tk入口仍保留。

源码运行：在frontend执行`npm ci`、`npm run build`，回根目录执行`.venv/Scripts/python.exe -m zhiyeteam.galaxy --demo`。打包使用`python tools/build_galaxy.py`，实体exe检查用`python tools/frozen_galaxy.py`；Windows需要Edge WebView2 Runtime。发行exe不要求Python/Node。

给B/C/D：[新版界面对接约定](docs/新版界面_BCD对接说明.md)。B/C的原接口不变，审计包装与日期/摘要扩展按该约定自动接入，契约测试不代表他们已完成实现。A个人交付与答辩见[知识星图说明](docs/A_知识星图交付说明.md)。下面的v1.0.0下载是保留的旧版，知识星图以对应PR/预览包为准。

用于软件工程团队验收的 Windows 桌面程序：记录 Markdown 笔记，按关键词和标签找回知识，用稳定 UUID 关联笔记，通过历史版本、回收站和完整备份保护内容。

团队版选择 Python + Tkinter + SQLite，以离线可运行、代码易讲解和四人可分工为首要目标。前两次实验的 .NET/Markdown 文件方案属于设计探索；本项目独立维护团队需求基线与实际实现说明。

![知页实际桌面窗口](docs/images/desktop.png)

## 交付与演示

- [Windows发布与报告](https://github.com/zemengzero/MSGA/releases/tag/v1.0.0)
- [四人分工与每次提交安排](docs/团队分工与提交计划.md)
- [D今晚的仓库统筹操作单](docs/D_仓库统筹操作单.md)
- [8分钟现场演示步骤](docs/现场演示步骤.md)
- [功能与代码定位](docs/功能与代码定位.md)
- 原始实际测试：`reports/test_results.json`、`reports/frozen_smoke.json`；尚未完成的真人反馈不写成已完成。

本项目使用小组已有的公开仓库`zemengzero/MSGA`，验收日期已确认2026年11月2日。掌握全员GitHub链接的同学担任D，负责协调协作权限、PR合并、发布和证据汇总；其他成员各用本人账号提交。

## 开发运行

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m zhiyeteam --demo
```

正式运行不带 `--demo`，默认将数据库保存到当前用户的本地应用数据目录。演示模式使用独立数据库，不覆盖正式笔记。

发布ZIP中的独立exe已在本机启动并验证真实窗口/保存。另一台未安装Python的机器仍需按D成员任务进行实测；本项目没有把本机检查冒称所有Windows版本兼容。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 团队提交约定

当前账号建立的基线不替代四位成员的贡献。每位成员使用自己的 GitHub 账号，在功能分支上实际修改、运行测试并提交，PR 中写明功能、代码位置、验证结果和已知限制。分工及逐次提交安排见 `docs/团队分工与提交计划.md`。

报告只记录实际执行的测试和反馈。用户反馈待真人试用后填写，不能把合成演示数据当作调研。最终要求以老师最新课堂说明为准。

## 重新生成报告

安装 `requirements-docs.txt` 后运行 `python tools/build_reports.py`；报告按当前源码AST提取函数位置，并读取真实测试JSON。PDF渲染使用Windows上的Chrome，已经生成的Word/PDF在发布包中，无需为了阅读文档安装这些开发依赖。

## 官方技术参考

- [Python SQLite在线备份](https://docs.python.org/3.13/library/sqlite3.html#sqlite3.Connection.backup)
- [PyInstaller打包说明](https://pyinstaller.org/en/stable/operating-mode.html)
- [GitHub提交邮箱与归属](https://docs.github.com/en/account-and-profile/concepts/email-addresses)

第三方运行库许可随发布文件的说明保留；本仓库未另行授予开源许可证。
