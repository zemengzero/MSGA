import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
const root = path.resolve("..");
let processHandle;
let url;
test.beforeAll(async () => {
  const run = "galaxy-e2e-" + Date.now();
  const info = path.join(root, "runtime", run + ".json");
  const venv = path.join(root, ".venv/Scripts/python.exe");
  processHandle = spawn(
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
    { cwd: root, windowsHide: true, stdio: "ignore" },
  );
  for (let i = 0; i < 100; i++) {
    if (fs.existsSync(info)) {
      url = JSON.parse(fs.readFileSync(info, "utf8")).url;
      return;
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("本地测试服务未启动");
});
test.afterAll(() => processHandle?.kill());
test.beforeEach(async ({ page }) => {
  await page.goto(url);
  await page.waitForFunction(() => window.__appReady);
});
async function call(page, action, payload = {}) {
  return page.evaluate(
    async ({ action, payload }) => {
      const r = await fetch("/api/" + action, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Zhiye-Token": window.ZHIYE_TOKEN,
        },
        body: JSON.stringify(payload),
      });
      return r.json();
    },
    { action, payload },
  );
}
test("真实笔记与关系组成3D图谱，资源全部来自本机", async ({ page }) => {
  const external = [];
  page.on("request", (r) => {
    if (!r.url().startsWith(url)) external.push(r.url());
  });
  await page.reload();
  await page.waitForFunction(() => window.__appReady);
  await expect(page.locator("canvas")).toHaveCount(1);
  const state = await call(page, "snapshot");
  expect(state.data.graph.nodes.length).toBe(30);
  expect(state.data.graph.links.length).toBe(60);
  await page.waitForTimeout(2600);
  expect(external).toEqual([]);
  await page.screenshot({
    path: path.join(root, "reports/A/galaxy-overview.png"),
  });
});
test("新建、编辑、自动保存、插入关联并在重载后读回", async ({ page }) => {
  await page.getByRole("button", { name: "新建笔记", exact: false }).click();
  await page.getByLabel("笔记标题").fill("星图端到端笔记");
  await page
    .getByLabel("Markdown正文")
    .fill("# 星图端到端验证\n\n这是一条真实保存的笔记。");
  await page.getByLabel("笔记标签").fill("端到端,课程");
  await expect(page.getByText("已保存到本机", { exact: true })).toBeVisible();
  const before = (await call(page, "snapshot", { query: "星图端到端笔记" }))
    .data.notes[0];
  expect(before).toBeTruthy();
  await page.getByRole("button", { name: "插入关联", exact: true }).click();
  await page.locator(".link-choices button").first().click();
  await expect(page.getByText("已保存到本机", { exact: true })).toBeVisible();
  const stored = (await call(page, "note", { id: before.id })).data;
  expect(stored.body).toContain("[[note:");
  const state = (await call(page, "snapshot")).data;
  expect(state.graph.links.some((l) => l.source === before.id)).toBeTruthy();
  await page.reload();
  await page.waitForFunction(() => window.__appReady);
  await page.getByLabel("搜索笔记", { exact: true }).fill("星图端到端笔记");
  await page
    .locator(".recent-item")
    .filter({ hasText: "星图端到端笔记" })
    .click();
  await expect(page.getByLabel("笔记标题")).toHaveValue("星图端到端笔记");
  await expect(page.locator(".markdown")).toContainText(
    "这是一条真实保存的笔记",
  );
  await page.screenshot({
    path: path.join(root, "reports/A/galaxy-editor.png"),
  });
});
test("版本冲突保留输入，取消离开不丢失缓冲", async ({ page }) => {
  const created = (
    await call(page, "create", { title: "冲突检查专用", body: "original" })
  ).data;
  await page.getByLabel("搜索笔记", { exact: true }).fill("冲突检查专用");
  await page
    .locator(".recent-item")
    .filter({ hasText: "冲突检查专用" })
    .click();
  await expect(page.getByLabel("笔记标题")).toHaveValue("冲突检查专用");
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await call(page, "save", {
    ...created,
    body: "external revision",
    revision: created.revision,
  });
  await page.getByLabel("Markdown正文").fill("我的尚未保存缓冲");
  await expect(
    page.getByText("保存失败，修改已保留", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Markdown正文")).toHaveValue("我的尚未保存缓冲");
  await page.getByRole("button", { name: "关闭笔记", exact: true }).click();
  await page.getByRole("button", { name: "返回编辑", exact: true }).click();
  await expect(page.getByLabel("Markdown正文")).toHaveValue("我的尚未保存缓冲");
  expect((await call(page, "note", { id: created.id })).data.body).toBe(
    "external revision",
  );
});
test("字号持久化不修改笔记；收藏与取消收藏有效", async ({ page }) => {
  const state = (await call(page, "snapshot")).data;
  const note = state.notes[0];
  await page.locator(".recent-item").first().click();
  await page.getByLabel("编辑器字号").selectOption("18");
  await expect
    .poll(async () => (await call(page, "snapshot")).data.font_size)
    .toBe(18);
  expect((await call(page, "note", { id: note.id })).data.revision).toBe(
    note.revision,
  );
  await page.reload();
  await page.waitForFunction(() => window.__appReady);
  await page.getByRole("button", { name: "偏好设置", exact: true }).click();
  await expect(page.getByLabel("设置字号")).toHaveValue("18");
  await page.getByRole("button", { name: "关闭窗口", exact: true }).click();
  await page.getByRole("button", { name: "全部笔记", exact: false }).click();
  await page
    .getByRole("button", { name: "收藏笔记", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "我的收藏", exact: true }).click();
  await expect(page.locator(".note-card")).toHaveCount(1);
  await page.getByRole("button", { name: "取消收藏", exact: true }).click();
  await expect(page.locator(".note-card")).toHaveCount(0);
});
test("回收站恢复、历史回退和安全预览保留原业务能力", async ({ page }) => {
  const note = (
    await call(page, "create", { title: "回收与历史检查", body: "first" })
  ).data;
  await call(page, "save", { ...note, body: "second" });
  await page.getByLabel("搜索笔记", { exact: true }).fill("回收与历史检查");
  await page
    .locator(".recent-item")
    .filter({ hasText: "回收与历史检查" })
    .click();
  await page.getByRole("button", { name: "历史版本", exact: true }).click();
  await page
    .locator(".version")
    .last()
    .getByRole("button", { name: "恢复", exact: true })
    .click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect(page.locator(".markdown")).toContainText("first");
  await page.getByRole("button", { name: "移入回收站", exact: true }).click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect(page.locator(".note-drawer")).toHaveCount(0);
  await page.getByRole("button", { name: "回收站", exact: true }).click();
  await page
    .locator(".note-card")
    .filter({ hasText: "回收与历史检查" })
    .click();
  await page.getByRole("button", { name: "恢复笔记", exact: true }).click();
  await page.getByRole("button", { name: "确定", exact: true }).click();
  await expect
    .poll(async () => (await call(page, "note", { id: note.id })).data.deleted)
    .toBe(false);
});
