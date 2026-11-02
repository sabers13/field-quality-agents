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

test("portfolio skills and actions use real destinations on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/?mode=replay#/");
  await expect(page.getByRole("list", { name: "Skills demonstrated in this project" })).toContainText("LangGraph");
  await expect(page.getByRole("link", { name: "GitHub source code (opens in a new tab)" })).toHaveAttribute("href", "https://github.com/sabers13/field-quality-agents");
  await expect(page.getByRole("link", { name: "Hire Me", exact: true })).toHaveAttribute("href", "https://sabersojudi.com/#contact");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("case loading reserves a preview, then offers recovery on failure", async ({ page }) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  let fail = true;
  await page.route("**/api/cases/2156317", async (route) => {
    await held;
    if (fail) {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Recorded case temporarily unavailable" }) });
    } else {
      await route.fulfill({ contentType: "application/json", body: JSON.stringify({ ...fixtures.case4, case: { ...(fixtures.case4.case as object), id: "2156317" } }) });
    }
  });
  await page.goto("/?mode=replay#/");
  const loading = page.getByRole("status").filter({ hasText: "Loading a recorded case…" });
  await expect(loading).toBeVisible();
  await expect(loading).toHaveAttribute("aria-busy", "true");
  expect(Math.round((await loading.boundingBox())!.height)).toBeGreaterThanOrEqual(420);
  await expect(page.locator(".example-preview")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Hire Me", exact: true })).toBeVisible();
  release();
  const error = page.getByRole("alert");
  await expect(error).toContainText("The example could not load");
  fail = false;
  await error.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("link", { name: "Explore a real case" })).toBeVisible();
  await expect(loading).toHaveCount(0);
});

test("opening state appears before the app and reduced motion remains still", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  let release!: () => void;
  const held = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/src/main.tsx", async (route) => { await held; await route.continue(); });
  const navigation = page.goto("/?mode=replay#/");
  await expect(page.getByRole("status").filter({ hasText: "Opening the evidence desk…" })).toBeVisible();
  expect(await page.locator(".boot-indicator").evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
  release();
  await navigation;
  await expect(page.locator(".boot-screen")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Explore a real case" })).toBeVisible();
  expect(await page.locator(".route-content").evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
  await page.getByRole("link", { name: "Explore a real case" }).click();
  await expect(page.getByRole("dialog", { name: "2156317" })).toBeVisible();
  expect(await page.locator(".sheet").evaluate((element) => getComputedStyle(element).animationName)).toBe("none");
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
  await page.getByRole("button", { name: "Dark theme", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.getByRole("button", { name: "Dark theme", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Light theme", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
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

test("data source chooser supports dismissal, keyboard selection and focus restoration", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/?mode=replay#/");
  const trigger = page.getByRole("button", { name: "Data source", exact: true });
  const choices = page.getByRole("group", { name: "Data source choices", exact: true });
  await expect(choices).not.toBeVisible();
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(choices.getByRole("button", { name: /^Recorded run/ })).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape");
  await expect(choices).not.toBeVisible();
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.locator(".recorded-status").click();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await trigger.click();
  await expect(choices.getByRole("button", { name: /^Saved results/ })).toBeDisabled();
  await page.keyboard.press("Tab");
  await expect(choices.getByRole("button", { name: /^Recorded run/ })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(choices.getByRole("button", { name: /^Live connection/ })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/mode=live/);
  await expect(trigger).toBeFocused();
  await trigger.click();
  await choices.getByRole("button", { name: /^Recorded run/ }).click();
  await expect(page).toHaveURL(/mode=replay/);
  await expect(choices).not.toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

for (const theme of ["light", "dark"] as const) {
  test(`overview and working views: ${theme} accessibility`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
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
