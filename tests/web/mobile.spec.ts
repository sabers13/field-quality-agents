import { expect, test } from "@playwright/test";

const PAGES = ["#/", "#/cases", "#/issues/I-2025-0001", "#/compare", "#/replay", "#/report"];

test.describe("360 px layout", () => {
  test("every page fits without horizontal page scroll", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    for (const hash of PAGES) {
      await page.goto(`/${hash}`);
      await expect(page.locator(".loading-dot")).toHaveCount(0);
      const overflow = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      expect(overflow.scrollWidth, `${hash} overflows`).toBeLessThanOrEqual(overflow.innerWidth + 1);
      await expect(page.getByRole("navigation", { name: "Primary, mobile" })).toBeVisible();
    }
  });

  test("the case board becomes a single column with a sticky status filter", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/#/cases");
    await expect(page.getByRole("group", { name: "Filter board by status" })).toBeVisible();
    await page.getByRole("button", { name: "Needs engineer", exact: true }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Needs engineer" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "New", exact: true })).toHaveCount(0);
  });

  test("case detail opens full screen and closes back to the board", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/#/cases");
    await page.getByRole("link", { name: /Open case C-2025-0006/ }).click();
    const dialog = page.getByRole("dialog", { name: "C-2025-0006" });
    await expect(dialog).toBeVisible();
    const box = await dialog.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(350);
    await dialog.getByRole("button", { name: "Close" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(page).toHaveURL(/#\/cases$/);
  });

  test("weekly and comparison metrics use the phone list layout", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    for (const hash of ["#/report", "#/compare"]) {
      await page.goto(`/${hash}`);
      await expect(page.locator(".metrics-table")).toBeHidden();
      await expect(page.locator(".metrics-list")).toBeVisible();
    }
  });

  test("the topbar menu reaches replay and weekly report", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await page.goto("/#/");
    await page.getByRole("button", { name: "Page menu" }).click();
    await page.getByRole("link", { name: "Replay" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Replay" })).toBeVisible();
  });
});
