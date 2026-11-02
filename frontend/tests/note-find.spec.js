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
  ], { cwd: root, windowsHide: true, stdio: "ignore" });
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
