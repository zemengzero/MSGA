# 知识星图界面与B/C/D对接约定

2026-11-02。此文是合并接口约定；B/C功能是否完成以各人真实PR为准，适配测试中的契约桩不代表成员已经实现功能。

## 现有代码与数据保持兼容

A新增frontend/、galaxy_api.py、galaxy_server.py、galaxy.py与独立打包入口，不改store.py、schema.sql、backup.py、search.py、links.py、transfer.py的业务接口。正式库继续使用LOCALAPPDATA/ZhiYeTeam/personal/notes.db；新演示库使用同级galaxy-demo，旧演示库和原Tk界面仍可单独运行。不要把演示库覆盖到正式库。

旧数据打开后只读取原Schema，不迁移、清空或重写笔记。图谱的节点来自有效笔记、连线来自links实际记录；回收站和失效目标从图谱隐藏，不删除正文标记。默认展示最近150篇，全部笔记仍可搜索。图谱不是AI推断关系。

## B：备份与审计

- B1继续在backup.create_backup内增加空间预检，函数成功返回Path不变；新界面已调用该函数，不另写一套备份。
- B2若新增zhiyeteam.restore_audit.restore_with_audit(store, source, protection_dir, audit_path)，新界面适配层会自动调用。成功结果应含protection_path与audit_warning，支持属性对象或同名键字典。
- audit_warning为空表示正常；非空时界面单独提示“恢复成功但审计写入失败”，不会伪装数据恢复失败。恢复本身失败时仍抛原有异常；回退失败继续设置store.writes_disabled，适配层会跨请求保留禁写状态。
- audit_path由适配层传入数据目录/audit/restore.jsonl。没有B2模块时仍调用原restore_backup，基础恢复可以正常工作。

## C：日期与命中摘要

- search.search_notes原四个参数与Note列表返回值保持不变。新增关键字参数updated_from、updated_before，均接收带时区datetime，区间[from, before)。
- 前端按北京时间UTC+08:00解释YYYY-MM-DD，结束日期转换为次日00:00。适配层通过函数签名识别日期能力，C合入后自动显示日期控件；未实现时隐藏控件，不伪造筛选。
- search_hits可放search.py或search_presenter.py。参数同search_notes，返回项含note、snippet、matched_fields，支持属性对象或字典。摘要用于列表excerpt，字段用于matched_fields，不改变图谱的实际关联。
- 新界面不假定search_notes改成SearchHit；这样旧Tk界面和旧测试也继续兼容。B/C不要并行修改共享ui.py；星图界面通常无需他们改React文件。

## D：运行、验证与打包

先合并A的PR #13，再合并B/C已通过的增量。原tools/build_exe.py仍构建Tk版，新版请使用tools/build_galaxy.py；两个exe互不覆盖。新构建器在对应模块实际存在时自动加入restore_audit/search_presenter隐藏导入，避免源码可用而打包漏模块。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-galaxy.txt
```

在frontend目录运行npm ci和npm run build，然后回项目根目录：

```powershell
.\.venv\Scripts\python.exe -m zhiyeteam.galaxy --demo
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

前端交互测试：在frontend运行npm test，需要本机Google Chrome；测试会创建独立本地服务和合成数据，不接触正式库。随后运行python tools/build_galaxy.py与python tools/frozen_galaxy.py验证独立exe。Windows需Edge WebView2 Runtime；exe本身不要求安装Python或Node，不能把需要WebView2说成没有运行时依赖。

对接测试：tests/test_galaxy_api.py覆盖B的审计结果与C的日期/摘要接口契约。B/C实际合入后还需跑各自真实实现测试以及最终集成演示；不要只凭契约桩宣称真实功能全通过。

## 责任与评审

A负责新界面、适配层、对应测试与个人说明；B负责备份业务/审计模块；C负责搜索业务/摘要模块；D负责审核合并、实际跨机验证、全组总报告与最终Release。保留每个人的实质提交，不改作者或日期。A本次参考Blinko的产品布局，没有复制其GPL源码；3D图谱使用react-force-graph-3d/Three.js，发布包保留第三方许可。
