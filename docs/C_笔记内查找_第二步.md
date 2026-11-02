# 当前笔记内查找：第二步（查找入口与命中计数）

负责人：万语，U202414607，GitHub `ZYQY218`。基线：第一步提交 `5068193`。本次经本人授权直接向 main 交付新增查找功能及验证材料。

## 当前功能

在笔记详情面板的只读“阅读”模式增加“笔记内查找”按钮。点击后显示独立输入框和“共 N 处”，输入框自动聚焦，空查询显示“请输入关键词”。匹配规则沿用第一步：中文字面子串、ASCII 不区分大小写、整段短语、保留重叠出现位置，按 Unicode 码点处理。

仅搜索正文预览中的可见文字（innerText），不搜索 Markdown 符号、链接 href 或其他 HTML 属性。使用被动 effect 在预览 DOM 引用挂载后读取文字，避免首次打开和编辑返回时误计为零。查询只存在于独立组件内存中，不调用保存 API，不修改正文、版本或修改时间，不改变全局搜索条件。

关闭查找或按 Esc 清空查询并收起输入框；关闭详情、通过链接切换笔记或进入编辑模式时组件卸载，查询状态清空。重新进入阅读模式默认收起。支持空正文及窄窗口。

**本步只有入口、输入和计数，没有正文命中高亮、当前命中位置、上一处/下一处或滚动定位。** 这些属于第三步。本次未改动现有列表摘要高亮，未拦截浏览器 Ctrl+F，未重打包 EXE。

## 修改位置

- `frontend/src/NoteFindPanel.jsx`：组件、局部状态、可见文字读取及命中数量。
- `frontend/src/main.jsx`：添加只读预览 ref 和按笔记 ID 隔离的组件入口；没有修改保存函数。
- `frontend/src/style.css`：仅追加 .note-find-* 范围内的样式。
- `frontend/tests/note-find.spec.js`：真实浏览器验收与原功能保护检查，使用独立测试库。

## 本地验收步骤

打开 `runtime/highlight-server.json` 中的本地 URL（已准备独立演示库）。如页面已开着，请刷新以加载新前端。

1. 全局搜索“笔记内查找验收”，打开该合成笔记，保持“阅读”模式。
2. 点击“笔记内查找”，输入“动态规划”：应显示“共 1 处”；该词在 Markdown 源文中被粗体标记分开，按可见文字仍能匹配。
3. 输入“AI”：应显示“共 2 处”；输入“aba”：应为 2 处重叠命中；输入“hidden-target”：应为 0（它只存在于链接地址）。
4. 用 Esc 或关闭按钮收起，再打开确认输入为空；关闭重开笔记或切换到编辑后返回阅读，同样清空。全局搜索条件和正文内容保持原样。

验收样例只存放于 `runtime/highlight-preview`，未修改正式个人库。本次交付截图：`docs/images/C-note-find-step2.png`；测试运行原图位于 `reports/screenshots/C-note-find-step2.png`。

## 验证记录

实际执行：

```powershell
node --test --test-reporter=tap frontend/unit-tests/note-find.test.mjs
# frontend 目录
pnpm run build
$env:PLAYWRIGHT_CHANNEL = "msedge"
# 使用独立 JSON 输出路径，避免覆盖 A 阶段报告。
pnpm exec playwright test note-find.spec.js --reporter=list,json
pnpm exec playwright test --reporter=list,json
```

匹配函数 15 项单元测试通过，日志 `reports/C_note_find_step2_unit_tests.txt`；前端生产构建成功，只有原有资源块体积非阻断提示。

新增两项浏览器验收通过，记录在 `reports/C_note_find_step2_browser_tests.json`：覆盖跨粗体可见文字、中文/ASCII/emoji、链接地址不计入、重叠计数、关闭/Esc/切换笔记/编辑返回清理、空正文、窄窗口及自动保存。测试还断言查询过程中没有 save 请求，前后正文、revision、updated_at 不变，预览 HTML 不变且没有插入 mark。

完整浏览器回归 **10 项全部通过**（1.8 分钟），结果另见 `reports/C_note_find_step2_full_browser_tests.json`，包含原有星图、编辑保存、版本冲突、日期、摘要高亮、回收站等流程。原 A 阶段报告在运行后恢复。Python 业务模块未修改，本轮没有重复运行 Python 测试。

## 推送前补充

新增浏览器测试沿用现有测试的启动规则：优先使用本地 `.venv/Scripts/python.exe`，不存在时使用 CI 已配置的 `python`，不要求 CI 额外创建本地同名虚拟环境。修正后重新执行两项浏览器验收，实际结果保存在 `reports/C_note_find_step2_browser_tests.json`。本次功能不包含第三步的正文高亮或命中跳转，也不更新 EXE 发布包。
