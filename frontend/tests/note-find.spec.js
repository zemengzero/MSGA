import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve("..");
let child, url;
test.beforeAll(async () => {
  const run = "note-find-step2-" + Date.now();
  const info = path.join(root, "runtime", run + ".json");
  const venv = path.join(root, ".venv/Scripts/python.exe");
  child = spawn(fs.existsSync(venv) ? venv : "python", [
    "-m", "zhiyeteam.galaxy", "--demo", "--server", "--data-dir",
    path.join(root, "runtime", run), "--server-info", info,
  ], { cwd: root, windowsHide: true, stdio: "ignore", env: { ...process.env, PYTHONPATH: path.join(root, "src") } });
  for (let i = 0; i < 100; i++) {
    if (fs.existsSync(info)) { url = JSON.parse(fs.readFileSync(info, "utf8")).url; return; }
    await new Promise(r => setTimeout(r, 150));
  }
  throw new Error("Note-find preview server did not start");
});
test.afterAll(() => child?.kill());
async function call(page, action, payload = {}) {
  const result = await page.evaluate(async ({ action, payload }) => {
    const response = await fetch("/api/" + action, { method: "POST",
      headers: { "Content-Type": "application/json", "X-Zhiye-Token": window.ZHIYE_TOKEN },
      body: JSON.stringify(payload) });
    return response.json();
  }, { action, payload });
  expect(result.ok).toBe(true);
  return result.data;
}
async function openCreated(page, title) {
  await page.getByLabel("搜索笔记", { exact: true }).fill(title);
  await page.locator(".recent-item").filter({ hasText: title }).click();
  await expect(page.getByLabel("笔记标题")).toHaveValue(title);
}

test("只读笔记内查找统计可见文本，不改正文，全局搜索与生命周期独立", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const second = await call(page, "create", { title: "查找第二篇", body: "second" });
  const body = '# 查找验收\n\n动**态规**划 AI ai 😀 ababa\n\n[链接文字](https://example.invalid/hidden-target)\n\n[[note:' + second.id + '|切换到第二篇]]';
  const first = await call(page, "create", { title: "查找第一篇验收", body });
  await openCreated(page, first.title);
  const preview = page.locator(".note-drawer .markdown");
  const originalHTML = await preview.innerHTML();
  let saveRequests = 0;
  page.on("request", r => { if (r.url().endsWith("/api/save")) saveRequests++; });
  const toggle = page.getByRole("button", { name: "笔记内查找", exact: true });
  const input = page.getByLabel("笔记内查找关键词", { exact: true });
  const result = page.getByLabel("笔记内查找结果", { exact: true });
  await toggle.click(); await expect(input).toBeFocused();
  for (const [query, count] of [["动态规划", 1], ["aI", 2], ["😀", 1], ["aba", 2],
                                ["hidden-target", 0], ["链接文字", 1]]) {
    await input.fill(query); await expect(result).toHaveText(`共 ${count} 处`);
  }
  await input.fill("  "); await expect(result).toHaveText("请输入关键词");
  await input.fill("动态规划");
  await expect(page.getByLabel("搜索笔记", { exact: true })).toHaveValue(first.title);
  expect(await preview.innerHTML()).toBe(originalHTML);
  await expect(preview.locator("mark")).toHaveCount(0);
  fs.mkdirSync(path.join(root, "reports/screenshots"), { recursive: true });
  await page.screenshot({ path: path.join(root, "reports/screenshots/C-note-find-step2.png") });
  await page.getByRole("button", { name: "关闭笔记内查找", exact: true }).click();
  await toggle.click(); await expect(input).toHaveValue("");
  await input.fill("AI"); await input.press("Escape");
  await expect(input).toHaveCount(0);
  await expect(page.getByTestId("note-drawer")).toBeVisible();
  await toggle.click(); await input.fill("AI");
  await preview.getByRole("link", { name: "切换到第二篇", exact: true }).click();
  await expect(page.getByLabel("笔记标题")).toHaveValue(second.title);
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  await expect(input).toHaveCount(0);
  await toggle.click(); await expect(input).toHaveValue("");
  await input.fill("second"); await expect(result).toHaveText("共 1 处");
  await page.getByRole("button", { name: "关闭笔记", exact: true }).click();
  await openCreated(page, first.title);
  await expect(input).toHaveCount(0);
  await toggle.click(); await expect(input).toHaveValue("");
  const after = await call(page, "note", { id: first.id });
  expect([after.body, after.revision, after.updated_at]).toEqual([first.body, first.revision, first.updated_at]);
  expect(saveRequests).toBe(0);
});

test("空正文与窄窗口可查，编辑时隐藏查找并保留自动保存", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const note = await call(page, "create", { title: "空正文查找验收", body: "" });
  await openCreated(page, note.title);
  await page.setViewportSize({ width: 800, height: 900 });
  const toggle = page.getByRole("button", { name: "笔记内查找", exact: true });
  const input = page.getByLabel("笔记内查找关键词", { exact: true });
  await toggle.click(); await input.fill("AI");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 0 处");
  const box = await input.boundingBox();
  const drawer = await page.getByTestId("note-drawer").boundingBox();
  expect(box.x + box.width).toBeLessThanOrEqual(drawer.x + drawer.width);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await expect(toggle).toHaveCount(0); await expect(input).toHaveCount(0);
  await page.getByLabel("Markdown正文").fill("😀 Ai Ai");
  await expect.poll(async () => (await call(page, "note", { id: note.id })).body).toBe("😀 Ai Ai");
  await page.getByRole("button", { name: "阅读", exact: true }).click();
  await toggle.click(); await expect(input).toHaveValue("");
  await input.fill("ai");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 2 处");
  await expect(page.locator(".note-drawer .markdown")).toHaveText("😀 Ai Ai");
});


async function highlightTexts(page, name) {
  return page.evaluate(name => Array.from(CSS.highlights.get(name) || [], range => range.toString()), name);
}

test("正文高亮跨Markdown节点和emoji，重叠命中可循环跳转并完整清理", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const body = '# 第三步\n\n😀 动**态规**划 与 动态规划。\n\nababa\n\n[可见链接](https://example.invalid/hidden-target)';
  const note = await call(page, "create", { title: "第三步跨节点验收", body });
  await openCreated(page, note.title);
  const preview = page.locator(".note-drawer .markdown");
  const original = await preview.innerHTML();
  const input = page.getByLabel("笔记内查找关键词");
  const current = page.getByLabel("当前命中位置");
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await input.fill("动态规划");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 2 处");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual(["动态规划", "动态规划"]);
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual(["动态规划"]);
  const initial = await page.evaluate(() => Array.from(CSS.highlights.get("note-find-current"))[0].startOffset);
  expect(initial).toBe(3); // Emoji takes two UTF-16 code units plus one space.
  await expect(current).toHaveText("第 1 处");
  await input.press("Enter"); await expect(current).toHaveText("第 2 处");
  await input.press("Shift+Enter"); await expect(current).toHaveText("第 1 处");
  await page.getByRole("button", { name: "上一处匹配" }).click();
  await expect(current).toHaveText("第 2 处");
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await expect(current).toHaveText("第 1 处");
  await input.fill("aba");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual(["ababa"]);
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await expect(current).toHaveText("第 2 处");
  expect(await page.evaluate(() => Array.from(CSS.highlights.get("note-find-current"))[0].startOffset)).toBe(2);
  await input.fill("不存在");
  await expect(page.getByRole("button", { name: "下一处匹配" })).toBeDisabled();
  await expect(current).toHaveText("第 0 处");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  await input.fill("可见链接");
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual(["可见链接"]);
  await expect(preview.getByRole("link", { name: "可见链接" })).toHaveAttribute("href", "https://example.invalid/hidden-target");
  expect(await preview.innerHTML()).toBe(original);
  await input.press("Escape");
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual([]);
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  expect(await preview.innerHTML()).toBe(original);
  const after = await call(page, "note", { id: note.id });
  expect([after.body, after.revision, after.updated_at]).toEqual([body, note.revision, note.updated_at]);
});

test("长文跳转只滚动详情正文，并清理切换编辑时的高亮", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const body = '目标词\n\n' + '普通段落中的正文内容。\n\n'.repeat(90) + '目标词 唯一终点';
  const note = await call(page, "create", { title: "第三步长文定位验收", body });
  await openCreated(page, note.title);
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await page.getByLabel("笔记内查找关键词").fill("目标词");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual(["目标词", "目标词"]);
  const windowScroll = await page.evaluate(() => window.scrollY);
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await expect(page.getByLabel("当前命中位置")).toHaveText("第 2 处");
  await expect.poll(() => page.locator(".drawer-content").evaluate(e => e.scrollTop)).toBeGreaterThan(1000);
  const visible = await page.evaluate(() => {
    const range = Array.from(CSS.highlights.get("note-find-current"))[0];
    const rect = range.getBoundingClientRect();
    const box = document.querySelector(".drawer-content").getBoundingClientRect();
    return rect.top >= box.top && rect.bottom <= box.bottom;
  });
  expect(visible).toBe(true);
  expect(await page.evaluate(() => window.scrollY)).toBe(windowScroll);
  fs.mkdirSync(path.join(root, "reports/screenshots"), { recursive: true });
  await page.screenshot({ path: path.join(root, "reports/screenshots/C-note-find-step3.png") });
  await page.getByLabel("笔记内查找关键词").fill("唯一终点");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 1 处");
  await expect.poll(() => page.locator(".drawer-content").evaluate(e => e.scrollTop)).toBeGreaterThan(1000);
  await page.locator(".drawer-content").evaluate(e => { e.scrollTop = 0; });
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await expect.poll(() => page.locator(".drawer-content").evaluate(e => e.scrollTop)).toBeGreaterThan(1000);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual([]);
  await expect(page.getByLabel("Markdown正文")).toHaveValue(body);
});

test("不支持CSS高亮时仍可统计和定位", async ({ page }) => {
  await page.addInitScript(() => { window.Highlight = undefined; });
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const note = await call(page, "create", { title: "第三步兼容验收", body: "AI ai" });
  await openCreated(page, note.title);
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await page.getByLabel("笔记内查找关键词").fill("ai");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 2 处");
  await expect(page.getByText("当前环境无法显示正文高亮，仍可查看命中数量。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await expect(page.getByLabel("当前命中位置")).toHaveText("第 2 处");
});


test("跨行、代码块空白和链接内部格式均映射到原始DOM", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const body = '😀\n\nA  \nB\n\n```\n  spaced   AI\nline\n```\n\n[跨**节点**链接](https://example.invalid/route)';
  const note = await call(page, "create", { title: "第三步空白映射验收", body });
  await openCreated(page, note.title);
  const preview = page.locator(".note-drawer .markdown");
  const original = await preview.innerHTML();
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  for (const query of ["A\nB", "spaced   AI\nline", "跨节点链接", "😀"]) {
    await page.getByLabel("笔记内查找关键词").fill(query);
    await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 1 处");
    await expect.poll(async () => (await highlightTexts(page, "note-find-current"))
      .map(text => text.replace(/\s/g, ""))).toEqual([query.replace(/\s/g, "")]);
    expect(await preview.innerHTML()).toBe(original);
  }
  await page.getByRole("button", { name: "关闭笔记", exact: true }).click();
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual([]);
});


test("第四步：查找后恢复历史版本会重算高亮，回收恢复后没有残留状态", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const note = await call(page, "create", { title: "第四步历史组合验收", body: "旧版本 目标词" });
  await call(page, "save", { ...note, body: "新版本 目标词 目标词" });
  await openCreated(page, note.title);
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await page.getByLabel("笔记内查找关键词").fill("目标词");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 2 处");
  await page.getByRole("button", { name: "下一处匹配" }).click();
  await page.getByRole("button", { name: "历史版本", exact: true }).click();
  await page.locator(".version").last().getByRole("button", { name: "恢复", exact: true }).click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect(page.locator(".note-drawer .markdown")).toHaveText("旧版本 目标词");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 1 处");
  await expect(page.getByLabel("当前命中位置")).toHaveText("第 1 处");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual(["目标词"]);
  await page.getByRole("button", { name: "移入回收站", exact: true }).click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect(page.getByTestId("note-drawer")).toHaveCount(0);
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  await page.getByRole("button", { name: "回收站", exact: true }).click();
  await page.locator(".note-card").filter({ hasText: note.title }).click();
  await page.getByRole("button", { name: "恢复笔记", exact: true }).click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect.poll(async () => (await call(page, "note", { id: note.id })).deleted).toBe(false);
  await page.getByRole("button", { name: "知识星图", exact: false }).click();
  await openCreated(page, note.title);
  await expect(page.getByLabel("笔记内查找关键词")).toHaveCount(0);
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await expect(page.getByLabel("笔记内查找关键词")).toHaveValue("");
});

test("第四步：查找后编辑遇保存失败，取消关闭仍保留缓冲并可再次保存", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const note = await call(page, "create", { title: "第四步关闭确认验收", body: "原始 AI" });
  await openCreated(page, note.title);
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await page.getByLabel("笔记内查找关键词").fill("AI");
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual(["AI"]);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await expect.poll(() => highlightTexts(page, "note-find-current")).toEqual([]);
  await page.route("**/api/save", route => route.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ ok: false, type: "ValidationError", error: "验收注入的保存失败" }) }));
  await page.getByLabel("Markdown正文").fill("我的未保存缓冲 AI");
  await expect(page.getByText("保存失败，修改已保留", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "关闭笔记", exact: true }).click();
  await page.getByRole("button", { name: "返回编辑", exact: true }).click();
  await expect(page.getByLabel("Markdown正文")).toHaveValue("我的未保存缓冲 AI");
  expect((await call(page, "note", { id: note.id })).body).toBe("原始 AI");
  await page.unroute("**/api/save");
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect.poll(async () => (await call(page, "note", { id: note.id })).body).toBe("我的未保存缓冲 AI");
  await page.getByRole("button", { name: "关闭笔记", exact: true }).click();
  await expect(page.getByTestId("note-drawer")).toHaveCount(0);
  await openCreated(page, note.title);
  await expect(page.locator(".note-drawer .markdown")).toHaveText("我的未保存缓冲 AI");
  await expect(page.getByLabel("笔记内查找关键词")).toHaveCount(0);
});

test("第四步：千处Unicode长文匹配可定位末项，窄窗口无溢出", async ({ page }) => {
  await page.goto(url); await page.waitForFunction(() => window.__appReady);
  const body = '😀 AI 课程段落。\n\n'.repeat(1000);
  const note = await call(page, "create", { title: "第四步千处长文验收", body });
  await openCreated(page, note.title);
  await page.setViewportSize({ width: 800, height: 900 });
  await page.getByRole("button", { name: "笔记内查找", exact: true }).click();
  await page.getByLabel("笔记内查找关键词").fill("aI");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 1000 处");
  await expect.poll(() => page.evaluate(() => CSS.highlights.get("note-find-all")?.size)).toBe(1000);
  await page.getByRole("button", { name: "上一处匹配" }).click();
  await expect(page.getByLabel("当前命中位置")).toHaveText("第 1000 处");
  await expect.poll(() => page.locator(".drawer-content").evaluate(e => e.scrollTop)).toBeGreaterThan(10000);
  const box = await page.getByLabel("笔记内查找关键词").boundingBox();
  const drawer = await page.getByTestId("note-drawer").boundingBox();
  expect(box.x + box.width).toBeLessThanOrEqual(drawer.x + drawer.width);
  const rangeText = await highlightTexts(page, "note-find-current");
  expect(rangeText).toEqual(["AI"]);
  fs.mkdirSync(path.join(root, "reports/screenshots"), { recursive: true });
  await page.screenshot({ path: path.join(root, "reports/screenshots/C-note-find-step4.png") });
  await page.getByLabel("笔记内查找关键词").fill("没有这个结果");
  await expect(page.getByLabel("笔记内查找结果")).toHaveText("共 0 处");
  await expect.poll(() => highlightTexts(page, "note-find-all")).toEqual([]);
  await expect(page.getByRole("button", { name: "下一处匹配" })).toBeDisabled();
  await expect(page.getByLabel("当前命中位置")).toHaveText("第 0 处");
  const after = await call(page, "note", { id: note.id });
  expect([after.body, after.revision, after.updated_at]).toEqual([body, note.revision, note.updated_at]);
});
