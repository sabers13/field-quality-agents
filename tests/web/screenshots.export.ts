import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

/**
 * Every dashboard page from the offline export, at 360 px and 1280 px, in
 * light and dark. Case and issue ids come from the bundle itself, so the
 * screenshots always show the real recorded run rather than fixtures.
 */

const OUT_DIR = resolve(process.env["FQA_SCREENSHOT_DIR"] ?? "test-results/export-screenshots");
const WIDTHS = [360, 1280] as const;
const THEMES = ["light", "dark"] as const;

interface BundleIds {
  caseId: string;
  issueId: string;
}

async function readIds(page: Page): Promise<BundleIds> {
  await page.goto("/#/");
  await expect(page.getByText("Cases in", { exact: false }).first()).toBeVisible();
  return (await page.evaluate(() => {
    const bundle = (
      window as unknown as {
        __FQA_BUNDLE__: {
          caseDetails: Record<string, { trace: unknown[] }>;
          issues: { id: string }[];
        };
      }
    ).__FQA_BUNDLE__;
    const cases = Object.entries(bundle.caseDetails).sort(
      ([leftId, left], [rightId, right]) =>
        right.trace.length - left.trace.length || leftId.localeCompare(rightId),
    );
    return {
      caseId: cases[0]?.[0] ?? "",
      issueId: bundle.issues[0]?.id ?? "",
    };
  })) as BundleIds;
}

async function capture(page: Page, width: number, theme: "light" | "dark") {
  mkdirSync(OUT_DIR, { recursive: true });
  await page.setViewportSize({ width, height: width === 360 ? 800 : 900 });
  await page.addInitScript((value) => window.localStorage.setItem("fqa-theme", value), theme);

  const { caseId, issueId } = await readIds(page);
  const pages = [
    { name: "command-centre", hash: "#/", ready: "Cases in" },
    { name: "case-board", hash: "#/cases", ready: "Search" },
    { name: "case-detail", hash: `#/cases/${caseId}`, ready: "Report narrative" },
    { name: "issue-room", hash: "#/issues", ready: "One room per cluster" },
    { name: "issue-detail", hash: `#/issues/${issueId}`, ready: "Cluster over time" },
    { name: "before-after", hash: "#/compare", ready: "Metrics side by side" },
    { name: "replay", hash: "#/replay", ready: "A recorded run, played day by day" },
    { name: "weekly-report", hash: "#/report", ready: "Report narrative" },
  ] as const;

  for (const view of pages) {
    await page.goto(`/${view.hash}`);
    await expect(page.getByText(view.ready, { exact: false }).first()).toBeVisible();
    await expect(page.locator(".loading-dot")).toHaveCount(0);
    if (view.name === "replay") {
      // Show the replay mid-play rather than its empty starting state.
      await page.getByRole("button", { name: "Play replay" }).click();
      await page.waitForTimeout(1400);
      await page.getByRole("button", { name: "Pause replay" }).click();
    }
    // Let the canvas charts settle before the capture.
    await page.waitForTimeout(500);
    const scrollHeight = await page.evaluate(() => document.documentElement.scrollHeight);
    await page.screenshot({
      path: resolve(OUT_DIR, `${view.name}-${width}-${theme}.png`),
      fullPage: width === 1280 && scrollHeight <= 5000,
    });
  }
}

test.describe("static export screenshots", () => {
  for (const width of WIDTHS) {
    for (const theme of THEMES) {
      test(`${width} ${theme}`, async ({ page }) => {
        await capture(page, width, theme);
      });
    }
  }
});
