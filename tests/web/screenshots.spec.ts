import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

const OUT_DIR = resolve(process.env["FQA_SCREENSHOT_DIR"] ?? "test-results/screenshots");

const PAGES = [
  { name: "command-centre", hash: "#/", ready: "Cases in" },
  { name: "case-board", hash: "#/cases", ready: "Search" },
  { name: "case-detail", hash: "#/cases/C-2025-0003", ready: "Report narrative" },
  { name: "issue-room", hash: "#/issues/I-2025-0001", ready: "Cluster over time" },
  { name: "before-after", hash: "#/compare", ready: "Metrics side by side" },
  { name: "replay", hash: "#/replay", ready: "A recorded run, played day by day" },
  { name: "weekly-report", hash: "#/report", ready: "Report narrative" },
] as const;

async function capture(page: Page, width: number, theme: "light" | "dark") {
  mkdirSync(OUT_DIR, { recursive: true });
  await page.setViewportSize({ width, height: width === 360 ? 800 : 900 });
  await page.addInitScript((value) => window.localStorage.setItem("fqa-theme", value), theme);
  for (const view of PAGES) {
    await page.goto(`/${view.hash}`);
    await expect(page.getByText(view.ready, { exact: false }).first()).toBeVisible();
    await expect(page.locator(".loading-dot")).toHaveCount(0);
    await page.screenshot({
      path: resolve(OUT_DIR, `${view.name}-${width}-${theme}.png`),
      fullPage: width === 1280,
    });
  }
}

test.describe("screenshots", () => {
  test("1280 light", async ({ page }) => {
    await capture(page, 1280, "light");
  });

  test("1280 dark", async ({ page }) => {
    await capture(page, 1280, "dark");
  });

  test("360 light", async ({ page }) => {
    await capture(page, 360, "light");
  });

  test("360 dark", async ({ page }) => {
    await capture(page, 360, "dark");
  });
});
