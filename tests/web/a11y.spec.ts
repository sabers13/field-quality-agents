import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const PAGES = [
  { name: "command", hash: "#/", ready: "Cases in" },
  { name: "cases", hash: "#/cases", ready: "Search" },
  { name: "case", hash: "#/cases/C-2025-0003", ready: "Report narrative" },
  { name: "issues", hash: "#/issues/I-2025-0001", ready: "Cluster over time" },
  { name: "compare", hash: "#/compare", ready: "Metrics side by side" },
  { name: "replay", hash: "#/replay", ready: "A recorded run, played day by day" },
  { name: "report", hash: "#/report", ready: "Report narrative" },
] as const;

async function open(page: Page, hash: string, ready: string, theme: "light" | "dark", width: number) {
  await page.setViewportSize({ width, height: width === 360 ? 800 : 900 });
  await page.addInitScript((value) => window.localStorage.setItem("fqa-theme", value), theme);
  await page.goto(`/${hash}`);
  await expect(page.getByText(ready, { exact: false }).first()).toBeVisible();
  await expect(page.locator(".loading-dot")).toHaveCount(0);
}

async function scan(page: Page, label: string) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const summary = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => node.target.join(" ")),
  }));
  expect(summary, `${label}: ${JSON.stringify(summary, null, 2)}`).toEqual([]);
}

for (const view of PAGES) {
  test(`axe: ${view.name} light desktop`, async ({ page }) => {
    await open(page, view.hash, view.ready, "light", 1280);
    await scan(page, `${view.name} light 1280`);
  });

  test(`axe: ${view.name} dark mobile`, async ({ page }) => {
    await open(page, view.hash, view.ready, "dark", 360);
    await scan(page, `${view.name} dark 360`);
  });
}

for (const view of PAGES.slice(0, 3)) {
  test(`axe: ${view.name} light tablet`, async ({ page }) => {
    await open(page, view.hash, view.ready, "light", 800);
    await scan(page, `${view.name} light 800`);
  });
}
