// Local audit: exercise the real downloaded A frontend with real C search.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve("..");
let child, url;
test.beforeAll(async () => {
  const run = "c-contract-" + Date.now();
  const info = path.join(root, "runtime", run + ".json");
  const venv = path.join(root, ".venv/Scripts/python.exe");
  child = spawn(
    fs.existsSync(venv) ? venv : "python",
    [
      "-m",
      "zhiyeteam.galaxy",
      "--demo",
      "--server",
      "--data-dir",
      path.join(root, "runtime", run),
      "--server-info",
      info,
    ],
    { cwd: root, windowsHide: true, stdio: "ignore", env: { ...process.env, PYTHONPATH: path.join(root, "src") } },
  );
  for (let i = 0; i < 100; i++) {
    if (fs.existsSync(info)) {
      url = JSON.parse(fs.readFileSync(info, "utf8")).url;
      return;
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("Audit backend did not start");
});
test.afterAll(() => child?.kill());
async function call(page, action, payload = {}) {
  return page.evaluate(
    async ({ action, payload }) => {
      const response = await fetch("/api/" + action, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Zhiye-Token": window.ZHIYE_TOKEN,
        },
        body: JSON.stringify(payload),
      });
      return response.json();
    },
    { action, payload },
  );
}
test("真实C摘要、命中字段与北京时间日期筛选接入A界面", async ({ page }) => {
  await page.goto(url);
  await page.waitForFunction(() => window.__appReady);
  await expect(page.getByLabel("开始日期", { exact: true })).toBeVisible();
  const created = await call(page, "create", {
    title: "C-contract-note",
    body: "before ".repeat(55) + "Cneedle42 after ".repeat(20),
    tags: ["audit"],
  });
  expect(created.ok).toBe(true);
  const response = await call(page, "snapshot", { query: "Cneedle42" });
  expect(response.ok).toBe(true);
  expect(response.data.capabilities.date_filters).toBe(true);
  expect(response.data.capabilities.hit_snippets).toBe(true);
  expect(response.data.notes[0].matched_fields).toEqual(["body"]);
  expect(response.data.notes[0].excerpt).toContain("Cneedle42");
  expect(response.data.notes[0].excerpt.length).toBeLessThanOrEqual(120);
  await page.getByLabel("搜索笔记", { exact: true }).fill("Cneedle42");
  const item = page
    .locator(".recent-item")
    .filter({ hasText: "C-contract-note" });
  await expect(item).toBeVisible();
  await expect(item.locator("p")).toContainText("Cneedle42");
  const day = new Date(
    new Date(created.data.updated_at).getTime() + 8 * 3600000,
  )
    .toISOString()
    .slice(0, 10);
  await page.getByLabel("开始日期", { exact: true }).fill(day);
  await page.getByLabel("结束日期", { exact: true }).fill(day);
  await expect(item).toBeVisible();
  const excluded = page.waitForResponse(
    async (r) =>
      r.url().endsWith("/api/snapshot") &&
      (await r.json()).data?.match_count === 0,
  );
  await page.getByLabel("结束日期", { exact: true }).fill("");
  await page.getByLabel("开始日期", { exact: true }).fill("2000-01-01");
  await page.getByLabel("结束日期", { exact: true }).fill("2000-01-01");
  await excluded;
  await expect(item).toHaveCount(0);
  await page.screenshot({
    path: path.join(root, "reports/A/C-date-filter-audit.png"),
  });
});


test("C高亮在最近笔记和卡片中正确处理emoji与HTML，清空查询后消失", async ({ page }) => {
  await page.goto(url);
  await page.waitForFunction(() => window.__appReady);
  const title = "C-highlight-visual";
  const body = '## 😀 动态规划 Ai ai <script>window.__highlightInjected=1</script>';
  await call(page, "create", { title, body, tags: ["highlight"] });
  await page.getByLabel("搜索笔记", { exact: true }).fill("动态规划 AI");
  const item = page.locator(".recent-item").filter({ hasText: title });
  await expect(item).toBeVisible();
  await expect(item.locator("mark")).toHaveText(["动态规划", "Ai", "ai"]);
  await expect(item.locator("p")).toHaveText(body);
  await expect(item.locator("script")).toHaveCount(0);
  expect(await page.evaluate(() => window.__highlightInjected)).toBeUndefined();
  const navigated = page.waitForResponse(r => r.url().endsWith("/api/snapshot") &&
    r.request().postDataJSON().query === "");
  await page.getByRole("button", { name: "全部笔记", exact: false }).click();
  await navigated;
  await expect.poll(() => page.locator(".note-card").count()).toBeGreaterThan(1);
  // Wait for the debounced query result, rather than a stale transition frame.
  const filtered = page.waitForResponse(r => r.url().endsWith("/api/snapshot") &&
    r.request().postDataJSON().query === "动态规划 AI");
  await page.getByLabel("搜索笔记", { exact: true }).fill("动态规划 AI");
  await filtered;
  await expect(page.locator(".note-card")).toHaveCount(1);
  const card = page.locator(".note-card").filter({ hasText: title });
  await expect(card.locator("mark")).toHaveText(["动态规划", "Ai", "ai"]);
  await expect(card.locator("p")).toHaveText(body);
  fs.mkdirSync(path.join(root, "reports/screenshots"), { recursive: true });
  await page.screenshot({ path: path.join(root, "reports/screenshots/C-highlight-main.png") });
  await page.getByLabel("搜索笔记", { exact: true }).fill("");
  await expect(card.locator("mark")).toHaveCount(0);
  await expect(card.locator("p")).toHaveText(body);
});
