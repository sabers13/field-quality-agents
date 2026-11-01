import { expect, test } from "@playwright/test";

/**
 * The Q8 end-to-end path over the real backend and the built dashboard:
 * open a case, approve its proposal, see it move to Decided, then open the
 * fleet issue the issue agent drafted.
 */
test("open a case, approve it, see it move, and open the issue", async ({ page }) => {
  await page.goto("/?mode=live#/cases/C-2025-0002");

  const detail = page.getByRole("dialog", { name: "C-2025-0002" });
  await expect(detail).toBeVisible();
  await expect(detail.getByRole("heading", { name: "Agent trace" })).toBeVisible();
  await expect(detail.getByRole("button", { name: "Approve" })).toBeVisible();

  await detail.getByRole("button", { name: "Approve" }).click();
  const modal = page.getByRole("dialog", { name: "Approve proposal" });
  await expect(modal).toBeVisible();
  await page.getByLabel(/Reason/).fill("Verified evidence and a proportionate test.");
  await page.getByRole("button", { name: "Approve decision" }).click();
  await expect(page.getByText("Decision recorded: approve.")).toBeVisible();

  await page.getByRole("button", { name: "Close" }).first().click();
  await expect(detail).toHaveCount(0);

  await page.goto("/?mode=live#/cases");
  await page.reload();
  const decided = page
    .locator("section.board-column")
    .filter({ has: page.getByRole("heading", { name: "Decided" }) });
  await expect(
    decided.getByRole("link", { name: /Open case C-2025-0002/ }),
  ).toBeVisible();

  await page.goto("/?mode=live#/issues");
  await expect(page.getByRole("heading", { level: 1, name: "Issue room" })).toBeVisible();
  const issueLink = page.getByRole("link", { name: /I-20250609-001/ });
  await expect(issueLink).toBeVisible();
  await issueLink.click();
  await expect(page.getByText("D4 · Root cause hypotheses")).toBeVisible();
  await expect(page.getByText("Decision memo:", { exact: false })).toBeVisible();
});
