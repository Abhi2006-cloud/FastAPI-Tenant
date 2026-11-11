import { test, expect } from "@playwright/test";

test.describe("Interactive Demo Smoke Test", () => {
  test("full multi-tenant demo flow: session -> overview -> upgrade gate -> switch to pro -> unlocked export", async ({
    page,
  }) => {
    // 1. Go to /login
    await page.goto("/login");

    // Click "Explore Interactive Demo"
    const demoButton = page.getByRole("button", { name: /Explore Interactive Demo/i });
    await expect(demoButton).toBeVisible();
    await demoButton.click();

    // 2. Land on /o/<org-id>/overview
    await page.waitForURL(/\/o\/[a-f0-9-]+\/overview/, { timeout: 15000 });
    expect(page.url()).toMatch(/\/o\/[a-f0-9-]+\/overview/);

    // 3. Assert overview shows usage numbers and infrastructure table
    await expect(page.getByText("Workspace Members")).toBeVisible();
    await expect(page.getByText("Total Files")).toBeVisible();
    await expect(page.getByText("Database Storage")).toBeVisible();
    await expect(page.getByText("Hourly Invites")).toBeVisible();
    await expect(page.getByText("Zero-Cost Infrastructure Stack")).toBeVisible();

    // Assert initial plan badge is "FREE"
    const planBadge = page.locator("header").getByText(/free/i);
    await expect(planBadge).toBeVisible();

    // 4. Click "Audit Logs" in sidebar
    const auditLink = page.getByRole("link", { name: /Audit Logs/i });
    await expect(auditLink).toBeVisible();
    await auditLink.click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/audit/, { timeout: 10000 });

    // 5. Click "Export CSV" -> assert UpgradeDialog opens saying audit_export requires pro
    // In free tier, the button is wrapped in FeatureGate which triggers UpgradeDialog
    const lockedExportButton = page.getByRole("button", { name: /Export CSV/i }).first();
    await expect(lockedExportButton).toBeVisible();
    await lockedExportButton.click();

    // UpgradeDialog opens
    await expect(page.getByText(/Upgrade Required/i)).toBeVisible();
    await expect(page.getByText(/audit_export/i)).toBeVisible();
    await expect(page.getByText(/requires the Pro/i)).toBeVisible();

    // Close the upgrade dialog by clicking the close button or pressing Escape
    await page.keyboard.press("Escape");
    await expect(page.getByText(/Upgrade Required/i)).not.toBeVisible();

    // 6. Click "Switch demo to Pro" button in the demo top banner
    const switchProButton = page.getByRole("button", { name: /Switch demo to Pro/i });
    await expect(switchProButton).toBeVisible();
    await switchProButton.click();

    // 7. Wait for entitlements to invalidate -> assert plan badge changes from "FREE" to "PRO"
    const proBadge = page.locator("header").getByText(/pro/i);
    await expect(proBadge).toBeVisible({ timeout: 10000 });

    // 8. Click "Export CSV" again -> assert download triggers without 402
    const unlockedExportButton = page.getByRole("button", { name: "Export CSV", exact: true });
    const downloadPromise = page.waitForEvent("download");
    await unlockedExportButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("audit-logs");
  });
});
