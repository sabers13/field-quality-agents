import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { fixtures, mockLiveApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockLiveApi(page);
  await page.route("**/api/cases/2156317", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({ ...fixtures.case4, case: { ...(fixtures.case4.case as object), id: "2156317" } }),
  }));
});

test("overview leads into a case, disclosures and browser Back", async ({ page }) => {
  await page.goto("/?mode=replay#/");
  await expect(page.getByRole("heading", { level: 1, name: "Field quality agents" })).toBeVisible();
  await expect(page.getByText("What these results cannot prove")).toBeVisible();
  await page.getByRole("link", { name: "Explore a real case" }).click();
  const dialog = page.getByRole("dialog", { name: "2156317" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Proposal", exact: true })).toBeVisible();
  await expect(dialog.locator(".trace")).not.toBeVisible();
  await dialog.locator("summary").filter({ hasText: "Agent trace" }).click();
  await expect(dialog.locator(".trace")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await page.goBack();
  await page.goBack();
  await expect(page).toHaveURL(/#\/$/);
});

test("results preserve caveats and download the same comparison", async ({ page }) => {
  await page.goto("/?mode=replay#/compare");
  await expect(page.getByText("Read the comparison with its limits")).toBeVisible();
  await expect(page.getByText(/simulated engineer approvals do not establish/i)).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download comparison" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("field-quality-comparison.json");
  const stream = await download.createReadStream();
  let body = "";
  for await (const chunk of stream!) body += chunk.toString();
  expect(JSON.parse(body)).toEqual(fixtures.comparison);
});

test("case list switches to the workflow board and search sends its query", async ({ page }) => {
  await page.goto("/?mode=replay#/cases");
  await expect(page.getByRole("list", { name: "Complaint reports" })).toBeVisible();
  await page.getByRole("button", { name: "Board", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Needs engineer", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "List", exact: true }).click();
  const request = page.waitForRequest((req) => new URL(req.url()).searchParams.get("q") === "heater");
  await page.getByLabel("Search", { exact: true }).fill("heater");
  await request;
});

test("mobile navigation, theme and skip link stay usable", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/?mode=replay#/cases");
  await page.getByLabel("Theme", { exact: true }).selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await skip.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#\/cases$/);
  await expect(page.locator("#main-content")).toBeFocused();
  await page.getByRole("navigation", { name: "Primary", exact: true }).getByRole("link", { name: "Replay", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Replay", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Play replay" }).click();
  await expect(page.locator(".replay-event").first()).toBeVisible();
  await page.getByRole("button", { name: "Pause replay" }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

for (const theme of ["light", "dark"] as const) {
  test(`overview and working views: ${theme} accessibility`, async ({ page }) => {
    await page.setViewportSize({ width: theme === "dark" ? 375 : 1280, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("fqa-theme", value), theme);
    for (const hash of ["/", "/cases", "/issues/I-2025-0001", "/compare", "/dashboard", "/replay", "/report"]) {
      await page.goto(`/?mode=replay#${hash}`);
      await expect(page.locator(".loading-dot")).toHaveCount(0);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      expect(results.violations.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) })), hash).toEqual([]);
    }
  });
}
