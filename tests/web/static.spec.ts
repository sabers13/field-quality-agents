import { expect, test } from "@playwright/test";

test.describe("static dashboard", () => {
  test("command centre shows KPIs, the feed and the mini comparison", async ({ page }) => {
    await page.goto("/#/");
    await expect(page.getByRole("heading", { level: 1, name: "Command centre" })).toBeVisible();
    await expect(page.getByText("Cases in", { exact: true })).toBeVisible();
    await expect(page.getByText("Bundled fixture data", { exact: false }).first()).toBeVisible();
    await expect(page.getByRole("table", { name: "Before and after headline metrics" })).toBeVisible();
    await expect(page.getByRole("list", { name: "Recent agent actions" }).getByRole("listitem").first()).toBeVisible();
  });

  test("case board shows six columns and opens a case", async ({ page }) => {
    await page.goto("/#/cases");
    await expect(page.getByRole("heading", { level: 1, name: "Case board" })).toBeVisible();
    for (const heading of ["New", "Intake", "Analysis", "Needs engineer", "Decided", "Issue-linked"]) {
      await expect(page.getByRole("heading", { level: 2, name: heading })).toBeVisible();
    }
    await expect(page.getByRole("link", { name: /Open case C-2025-0003/ })).toBeVisible();
  });

  test("case detail shows the narrative, verified quotes, proposal, decision and trace", async ({ page }) => {
    await page.goto("/#/cases/C-2025-0003");
    const dialog = page.getByRole("dialog", { name: "C-2025-0003" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { level: 3, name: "Report narrative" })).toBeVisible();
    await expect(dialog.locator("mark.quote")).toHaveCount(3);
    await expect(dialog.locator("mark.quote-unverified")).toHaveCount(2);
    await expect(dialog.locator("mark.quote-verified")).toHaveCount(1);
    await expect(dialog.getByRole("heading", { level: 3, name: "Proposal" })).toBeVisible();
    await expect(dialog.getByText("Run a 2-hour low-temperature heater circuit test")).toBeVisible();
    await expect(dialog.getByText(/Static export: this page is read-only/)).toBeVisible();
    await expect(dialog.getByRole("heading", { level: 3, name: "Agent trace" })).toBeVisible();
    await expect(dialog.getByText("Step 7")).toBeVisible();
    await expect(dialog.getByRole("heading", { level: 3, name: "Similar cases" })).toBeVisible();
  });

  test("a decided case shows its recorded decision and read-only actions", async ({ page }) => {
    await page.goto("/#/cases/C-2025-0005");
    const dialog = page.getByRole("dialog", { name: "C-2025-0005" });
    await expect(dialog.getByText("Approved the targeted test", { exact: true }).first()).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Approve" })).toHaveCount(0);
    await expect(dialog.getByText(/Static export: this page is read-only/)).toBeVisible();
  });

  test("issue room renders the cluster chart, evidence, 8D and memo", async ({ page }) => {
    await page.goto("/#/issues/I-2025-0001");
    await expect(page.getByRole("heading", { level: 1, name: "Issue room" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Moisture ingress in rear lamp assemblies" })).toBeVisible();
    await expect(page.getByRole("img", { name: /Weekly reports for Moisture ingress/ })).toBeVisible();
    await expect(page.getByText("D4 · Root cause hypotheses")).toBeVisible();
    await expect(page.getByText("Decision memo: contain the Nimbus rear lamp seal")).toBeVisible();
    await expect(page.getByText("not verified").first()).toBeVisible();
  });

  test("before vs after shows metrics and both example directions", async ({ page }) => {
    await page.goto("/#/compare");
    await expect(page.getByRole("heading", { level: 1, name: "Before vs after" })).toBeVisible();
    await expect(page.getByRole("row", { name: /Quote grounding/ })).toBeVisible();
    await expect(page.getByText("Where the agent found what the linear pipeline missed")).toBeVisible();
    await expect(page.getByText("Where the linear pipeline was right")).toBeVisible();
    await expect(page.getByText("C-2025-0006", { exact: false }).first()).toBeVisible();
  });

  test("replay plays, pauses and changes speed", async ({ page }) => {
    await page.goto("/#/replay");
    await expect(page.getByRole("heading", { level: 1, name: "Replay" })).toBeVisible();
    await page.getByRole("button", { name: "Play replay" }).click();
    await expect(page.locator(".replay-event")).toHaveCount(1);
    await page.getByRole("button", { name: "Pause replay" }).click();
    const stopped = await page.getByLabel(/Position:/).inputValue();
    await expect(page.locator(".replay-event")).toHaveCount(Number(stopped));
    await page.getByLabel("Speed").selectOption("4");
    await expect(page.getByLabel("Speed")).toHaveValue("4");
    await page.getByRole("button", { name: "Play replay" }).click();
    await expect
      .poll(async () => Number(await page.getByLabel(/Position:/).inputValue()))
      .toBeGreaterThan(Number(stopped));
  });

  test("weekly report shows counts, narrative and metrics", async ({ page }) => {
    await page.goto("/#/report");
    await expect(page.getByRole("heading", { level: 1, name: "Weekly report" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: /24 cases received, 19 decided/ })).toBeVisible();
    await expect(page.getByText("Twenty-four reports arrived")).toBeVisible();
    await expect(page.getByRole("row", { name: /Quote grounding/ })).toBeVisible();
  });

  test("navigation keeps the current page marked", async ({ page }) => {
    await page.goto("/#/compare");
    await expect(page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Before vs after" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
