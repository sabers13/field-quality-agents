import { expect, test } from "@playwright/test";

import { mockLiveApi } from "./helpers";

test.describe("live decisions keyboard flow", () => {
  test("approve opens from the keyboard, Escape restores focus, and Enter submits", async ({ page }) => {
    await mockLiveApi(page);
    await page.goto("/?mode=live#/cases/C-2025-0004");

    const dialog = page.getByRole("dialog", { name: "C-2025-0004" });
    await expect(dialog).toBeVisible();
    const approve = dialog.getByRole("button", { name: "Approve" });
    await expect(approve).toBeVisible();

    await approve.focus();
    await page.keyboard.press("Enter");
    const modal = page.getByRole("dialog", { name: "Approve proposal" });
    await expect(modal).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(modal).toHaveCount(0);
    await expect(approve).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(modal).toBeVisible();
    await page.getByLabel(/Reason/).fill("Verified evidence and a proportionate test.");
    const submit = page.getByRole("button", { name: "Approve decision" });
    await submit.focus();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Decision recorded: approve.")).toBeVisible();
  });

  test("override requires a reason and posts the edited proposal", async ({ page }) => {
    let posted: Record<string, unknown> | null = null;
    await mockLiveApi(page, { onDecision: (body) => (posted = body) });
    await page.goto("/?mode=live#/cases/C-2025-0004");

    const dialog = page.getByRole("dialog", { name: "C-2025-0004" });
    const override = dialog.getByRole("button", { name: "Override" });
    await override.click();
    const modal = page.getByRole("dialog", { name: "Override proposal" });
    await expect(modal).toBeVisible();

    const submit = page.getByRole("button", { name: "Override decision" });
    await expect(submit).toBeDisabled();
    await page.getByLabel("Proposal summary").fill("Run a 6-hour humidity soak on the harness");
    await page.getByLabel(/Reason/).fill("Six hours covers the condensation cycle.");
    await expect(submit).toBeEnabled();
    await submit.click();

    await expect(page.getByText("Decision recorded: override.")).toBeVisible();
    expect(posted).not.toBeNull();
    expect(posted).toMatchObject({
      action: "override",
      rationale: "Six hours covers the condensation cycle.",
      edited_proposal: { summary: "Run a 6-hour humidity soak on the harness" },
    });
  });

  test("ask keeps the case with the engineer", async ({ page }) => {
    let posted: Record<string, unknown> | null = null;
    await mockLiveApi(page, { onDecision: (body) => (posted = body) });
    await page.goto("/?mode=live#/cases/C-2025-0004");
    await page.getByRole("button", { name: "Ask" }).click();
    await page.getByLabel(/Reason/).fill("Which build month is affected?");
    await page.getByRole("button", { name: "Ask decision" }).click();
    await expect(page.getByText("Decision recorded: ask.")).toBeVisible();
    expect(posted).toMatchObject({ action: "ask" });
  });

  test("the live mode reports a disconnected stream without blocking the page", async ({ page }) => {
    await mockLiveApi(page);
    await page.goto("/?mode=live#/dashboard");
    await expect(page.getByText("Connection interrupted", { exact: true })).toBeVisible();
    await expect(page.getByText("Cases in", { exact: true })).toBeVisible();
  });
});
