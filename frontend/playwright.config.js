import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  fullyParallel: false,
  // GitHub Windows runners with SwiftShader can take longer to reload the 3D UI.
  timeout: 90000,
  expect: { timeout: 10000 },
  use: {
    channel: "chrome",
    headless: true,
    viewport: { width: 1460, height: 940 },
    launchOptions: {
      args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  reporter: [
    ["list"],
    ["json", { outputFile: "../reports/A/galaxy-e2e.json" }],
  ],
});
