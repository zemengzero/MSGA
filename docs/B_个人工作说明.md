# B个人工作说明：数据保护与备份恢复

## 1. 工作范围

本次在 `feature/b-backup-policy` 分支完成 B1、B2、B3 的代码与测试增量：

- B1：备份前空间预检；
- B2：恢复结果隐私审计；
- B3：空间不足、审计失败、恢复回退等故障回归。

未修改 `src/zhiyeteam/ui.py`、`src/zhiyeteam/search.py` 或其他成员的测试文件。PR #16 已把最新 `origin/main`（`db2555c`）合并进 B 分支，该基线包含 A 的 galaxy 界面、C 的搜索扩展和最新笔记查找界面。

## 2. B1：备份前空间预检

主要位置：

- `src/zhiyeteam/backup.py`
- `_estimated_snapshot_bytes`
- `_nearest_existing_directory`
- `_check_snapshot_space`
- `create_backup`

实现内容：

1. 使用 `PRAGMA page_count` 乘以 `PRAGMA page_size` 估算快照字节数。
2. 安全余量取 16 MiB 与估算值 10% 中的较大者，10% 部分向上取整。
3. 当目标目录不存在时，从目标父目录向上查找最近的已存在目录，并使用该目录所在卷的 `shutil.disk_usage(...).free`。
4. 可用空间小于“预估大小加安全余量”时抛出 `ValidationError`，错误文本包含预计需求和当前可用空间。
5. 空间检查发生在创建目标目录、`.partial` 文件和 SQLite 临时文件之前。
6. `restore_backup` 创建恢复前保护副本时继续调用 `create_backup`，因此保护副本也受到同一预检约束；同时移除了提前创建保护目录的步骤，使失败时不留空目录。
7. 原有目标已存在、目标等于当前库、事务未结束等检查顺序和异常契约保留。

限制：该检查是保守预检，不承诺精确预测文件系统元数据、WAL、并发写入或其他进程的后续空间占用。预检通过后实际写入仍可能失败，原有 `AppError`、`OSError`、临时文件清理和恢复回退逻辑继续负责这些情况。

## 3. B2：恢复结果审计

新增模块：`src/zhiyeteam/restore_audit.py`。

接口：

```python
restore_with_audit(
    store,
    source,
    protection_dir,
    audit_path,
    *,
    restore_impl=None,
) -> RestoreReport
```

返回对象：

```python
@dataclass(frozen=True)
class RestoreReport:
    protection_path: Path
    audit_warning: str
    operation_id: str
```

语义：

- 数据恢复成功时返回真实保护副本路径。
- `restore_impl` 为可选的底层恢复函数注入点，默认调用 `restore_backup`；Galaxy API 用它保留对故障测试和替代实现的兼容性。
- 审计写入成功时 `audit_warning` 为空。
- 审计写入失败时不回滚、不重做恢复，返回“数据恢复成功，但审计记录未写入”。
- 数据恢复失败时尝试写入失败事件，再重新抛出原始恢复异常；审计异常不会覆盖原始异常。
- `restore_backup` 的原有签名、返回 `Path` 的成功行为和异常类型保持不变。

审计文件采用 UTF-8 JSONL，每次操作写入开始、成功或失败事件。记录字段包括：

- 随机操作 ID；
- UTC 时间；
- 事件类型；
- 备份文件名；
- 可获取的保护副本文件名；
- 异常类型名称；
- `writes_disabled` 状态。

审计记录只保存文件名，不保存完整路径、正文、笔记标题、异常消息或含路径的整段错误文本。恢复失败发生在保护副本创建之前时，保护文件名留空。

D 接入恢复入口时，建议使用：

```python
from pathlib import Path

from zhiyeteam.restore_audit import restore_with_audit

data_dir = Path(data_dir)
report = restore_with_audit(
    store,
    source,
    data_dir / "backups",
    data_dir / "audit" / "restore.jsonl",
)

status = f"恢复完成；恢复前数据保留在：{report.protection_path}"
if report.audit_warning:
    status += f"；{report.audit_warning}"
```

审计文件必须放在不会被备份恢复替换的位置，示例中使用数据目录下的独立 `audit` 子目录。

## 4. B3：故障回归

新增测试：`tests/test_backup_policy.py`。

| 验收项 | 测试覆盖 |
| --- | --- |
| B-T01 空间充足 | `test_b01_sufficient_space_creates_valid_backup_without_changing_store` |
| B-T02 空间不足 | `test_b02_insufficient_space_refuses_before_creating_target_or_partial` |
| B-T03 多层新目录 | `test_b03_nested_target_uses_nearest_existing_parent_volume` |
| B-T04 保护目录空间不足 | `test_b04_protection_space_failure_stops_before_restore` |
| 保护副本未生成前失败 | `test_failure_before_protection_records_blank_protection_file` |
| B-T05 正常恢复审计 | `test_b05_success_audit_is_correlated_and_private` |
| B-T06 审计目录不可写 | `test_b06_audit_write_failure_does_not_redo_successful_restore` |
| B-T07 恢复失败与审计失败 | `test_b07_failed_restore_records_failure_without_error_text_or_paths`、`test_b07_audit_failure_does_not_mask_original_restore_error` |
| B-T08 恢复和回退均失败 | `test_b08_double_failure_disables_writes_and_audits_protection` |

测试不仅检查调用次数，还检查实际文件、数据库内容、revision、保护副本、JSONL 字段、隐私内容和禁写状态。

## 5. 实际测试结果

执行命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

实际结果：

```text
Ran 117 tests in 8.228s

OK
```

其中最新 main 的原有测试全部保留并通过，新增 B 专项测试 10 项全部通过。完整输出见 `reports/B/test-log.txt`，结构化摘要见 `reports/B/unit_checks.json`。

前端按 CI 等价步骤另行验证：

```text
npm ci             成功，安装 67 个包，0 个漏洞
npm run build      成功
node --test        17 passed
playwright test    17 passed
```

其中此前偶发失败的“版本冲突保留输入”用例，在隔离运行、完整套件重复运行和干净 `npm ci` 后运行中均通过。

后续 PR CI 又在“字号持久化”用例的 `page.reload()` 处触发 40 秒单测试超时。核对提交关系后确认，`integration/ac-galaxy-release`（`65fdfb8`）已经是 `main`（`5698dbf`）的祖先，B 分支没有修改前端源码，因此不是界面与前端版本不匹配。失败属于 GitHub Windows 运行器使用 SwiftShader 时的整体加载波动。已将 Playwright 单测试上限从 40 秒调整为 90 秒，测试断言和业务行为不变。

## 6. 90秒演示

1. 先说明：空间预检用于避免明显不足，但不能替代实际写入异常处理和恢复回退。
2. 创建一条合成演示笔记，创建一个备份，再修改当前笔记。
3. 调用 `restore_with_audit` 恢复备份，展示返回的保护副本路径和独立 `audit/restore.jsonl`。
4. 打开 JSONL，说明开始与成功事件具有同一个随机操作 ID，且没有正文、标题或完整路径。
5. 运行 B-T02，展示空间不足时没有目标文件、没有 `.partial` 文件，正文和 revision 未改变。
6. 运行 B-T06，说明审计失败时恢复仍成功，但返回非致命警告，且没有第二次恢复。

## 7. 能回答的问题

### 空间估算依据是什么？

使用 SQLite 当前 `page_count * page_size` 估算数据库页占用的字节数，再增加 16 MiB 或 10% 中较大的安全余量。该值用于预检，不是对文件系统实际额外开销的精确承诺。

### 为什么预检通过仍可能写失败？

其他进程可能继续占用空间，文件系统元数据、WAL、权限变化、磁盘配额和并发操作都可能使实际写入失败。因此预检不能替代 `OSError`、`sqlite3.Error`、临时文件清理和恢复回退。

### 为什么审计不放在备份会覆盖的 SQLite 库中？

完整恢复会用备份替换当前数据库。如果审计写在同一个库中，恢复会把恢复前的审计记录一起替换，无法保留真实操作轨迹。因此使用独立 JSONL 文件。

### 恢复成功但审计失败时怎样避免误报？

数据恢复只执行一次。恢复成功后，如果审计写入失败，函数返回成功保护路径并附带非致命警告，不再次恢复或回滚，也不把恢复本身报告为失败。

### 保护或回退失败后为什么禁写？

恢复和回退都失败意味着当前数据库内容处于不可确认状态。继续写入可能覆盖可用恢复线索，因此设置 `store.writes_disabled = True`，要求用户使用提示的保护副本重新打开。

## 8. 已知限制与待D完成

- 本分支没有修改界面，D 需要把恢复入口切换到 `restore_with_audit` 并展示保护位置和审计警告。
- UI 集成截图和实体程序演练待 D 合并后完成。
- 本地提交作者已设置为 `DKLSOUL <2553675108@qq.com>`。变基后的 B1 提交为 `2f721b7`，B2 提交为 `1344730`，B3 提交为 `ae7a711`，CI 兼容修复由后续提交保存。
- 本机已使用便携 Node 24 完成 `npm ci`、`npm run build`、17 项 note-find 单元测试和 17 项 Playwright 测试；Python 117 项与前端两组 17 项测试均已实际通过。
