# 当前笔记内查找：第四步验收与交接 / Final acceptance and handoff

负责人：万语，U202414607，GitHub `ZYQY218`。基线为第三步 `9113605`。本轮在本地验收完成后按本人授权提交 main；没有重新打包 EXE 或更新 Release。

## 四步交付范围 / Four-step delivery

1. `5068193`：独立可见文本匹配函数，字面短语、ASCII 大小写、Unicode 码点和重叠结果。
2. `97a6f76`：只读详情查找入口、输入、计数及关闭/切换时清理。
3. `9113605`：原生 CSS 高亮、当前命中、循环跳转、多行、跨节点映射和正文定位。
4. 本次：新增三项组合验收，把匹配单元测试接入现有 CI，完成全量回归、操作说明、截图和演示交接。前三步业务实现无需再修改。

English: completes acceptance and handoff for the existing in-note finder. Adds history/restore interaction, failed-save leave guards and 1,000-hit Unicode stress coverage, plus a CI unit-test gate. No new application behavior or database migration is introduced in this step.

## 验收矩阵

| 场景 | 自动化证据 | 要求 |
| --- | --- | --- |
| 中文、ASCII 大小写、emoji、字面短语、空查询、无结果 | `frontend/unit-tests/note-find.test.mjs`；`note-find.spec.js` | 范围/计数正确，空查询或无结果无残留高亮 |
| 30 万字符重复前缀、500 组确定性对照 | 匹配单元测试 | 与独立简单算法结果一致，长文无二次方扫描 |
| 跨粗体、链接、br、代码块、多行输入 | 第三步 DOM 映射测试 | 显示文字可检索，href 不计入，码点转换无错位 |
| 重叠、紧邻、第一/最后命中、单命中重新定位 | 单元/浏览器查找测试 | 保留原命中数，上下循环，DOM 覆盖合并不改原结果 |
| 关闭/Esc/切换/编辑/无 Highlight API | 第二、三步生命周期与兼容测试 | 清理自身高亮，正文和链接不变，旧环境保留统计/定位 |
| 查找后历史恢复及回收恢复 | 本次新增“第四步历史组合验收” | 新正文重新计数、当前位置回到第一处，关闭/恢复后无残留状态 |
| 查找后编辑、保存失败、取消关闭、重试保存 | 本次新增“第四步关闭确认验收” | 未保存缓冲保留，取消关闭不丢内容，故障解除后可正常保存 |
| 千处 emoji 长文、800px 窄窗口、末项定位 | 本次新增“第四步千处长文验收” | 1000 个实际范围，末项可见，控件不溢出，查询不改内容/版本/时间 |
| 原全局搜索、日期摘要、字号收藏、自动保存、冲突、历史回收 | 原 `galaxy*.spec.js` 全部保留 | 完整浏览器回归通过，无查找引入的业务退化 |
| 后端搜索、关联、备份、导入导出及 UI guards | Python 完整 unittest | 原业务回归通过 |

所有笔记均为隔离临时库中的合成数据，不是真人反馈。故障测试通过拦截保存响应注入失败，不改真实用户数据库。

## 运行与证据

实际运行命令：

```powershell
# 仓库根目录
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test --test-reporter=tap frontend/unit-tests/note-find.test.mjs
# frontend 目录
pnpm run build
$env:PLAYWRIGHT_CHANNEL = "msedge"
# 各次执行通过 PLAYWRIGHT_JSON_OUTPUT_FILE 保存到独立 C 报告。
pnpm exec playwright test note-find.spec.js --grep "第四步" --reporter=list,json
pnpm exec playwright test --reporter=list,json
```

实际结果 / Results：**107 项 Python 测试通过（5.015 秒）、17 项匹配单元测试通过、17 项浏览器流程通过（2.4 分钟）、前端构建成功**。新增三项组合验收另行先通过（46.0 秒），然后纳入完整回归。截图已检查：800px 窄窗口显示第 1000 处并正常定位，无控件溢出。

报告：`reports/C_note_find_step4_python_tests.txt`、`C_note_find_step4_unit_tests.txt`、`C_note_find_step4_build.txt`、`C_note_find_step4_targeted_browser_tests.json`、`C_note_find_step4_full_browser_tests.json`。机器可读汇总为 `C_note_find_step4_acceptance.json`，记录通过数量、源码 SHA-256 和验证基线。旧阶段报告保持原样；原 A 阶段截图和报告在执行后恢复。

CI 在原有 `galaxy-frontend.yml` 的 npm ci 后增加 `npm run test:note-find`；之后继续原前端构建和全量 Playwright。没有放宽失败退出码，也不新增依赖。云端 CI 在推送后执行，本机通过不冒称云端已经通过。

## 操作与 90 秒演示

使用本地独立预览（URL 见 runtime/highlight-server.json），刷新后打开“笔记内查找第三步验收”：

- 0–20 秒：阅读模式点击“笔记内查找”，输入“动态规划”，观察总数 3、第一处橙色、其他浅黄；第一处跨粗体节点。
- 20–40 秒：点击下一处直至最后一处，观察只滚动正文；Enter 下一处、Shift+Enter 上一处，末尾回到第一处。
- 40–55 秒：查询 aba，观察重叠匹配为 2，切换当前区域；输入不存在的文字，观察清理高亮并禁用按钮。
- 55–70 秒：Esc 关闭，再打开输入为空；切换编辑，演示查找隐藏但原正文保留，返回阅读查询不残留。
- 70–90 秒：展示最终报告、历史/关闭失败组合测试及千处长文截图，解释 CSS 高亮没有替换 HTML 或修改正文。

新增千处长文验收截图：`docs/images/C-note-find-step4.png`。原完整高亮截图及逐步实现说明分别见 `C_笔记内查找_第一步.md`、`C_笔记内查找_第二步.md`、`C_笔记内查找_第三步.md`。

## 实际限制

只读正文预览可查找，编辑器内暂不接入；标题和链接地址不参与正文查找。Enter 用于跳转，显式换行可通过粘贴输入。不覆盖浏览器原有 Ctrl+F。

高亮需要当前 Edge/Chrome 的 CSS Custom Highlight API；缺少该能力时按已测回退保留计数及可映射位置的定位。可见文字如果被未来 CSS 转换到无法映射，则拒绝绘制错误范围。

千处长文为功能压力回归，不是整机时延或所有设备性能保证。本轮为 Windows + Edge 本机源码验收，未把它写成跨机、真人体验或新 EXE 验收；这些不在本次四步源码任务范围内。
