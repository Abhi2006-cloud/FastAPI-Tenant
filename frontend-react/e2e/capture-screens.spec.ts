import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screensDir = path.resolve(__dirname, "../../docs/screens");

test.describe("Capture UI Screenshots", () => {
  test("capture desktop (1440px) screenshots", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });

    // Login and launch demo
    await page.goto("/login");
    const demoButton = page.getByRole("button", { name: /Explore Interactive Demo/i });
    await expect(demoButton).toBeVisible();
    await demoButton.click();

    await page.waitForURL(/\/o\/[a-f0-9-]+\/overview/, { timeout: 15000 });
    const currentUrl = page.url();
    const orgIdMatch = currentUrl.match(/\/o\/([a-f0-9-]+)\/overview/);
    expect(orgIdMatch).not.toBeNull();
    const orgId = orgIdMatch![1];

    // 1. Overview
    await expect(page.getByRole("heading", { name: /Overview/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "overview-desktop.png"), fullPage: false });

    // 2. Members
    await page.getByRole("link", { name: /^Members$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/members/);
    await expect(page.getByRole("heading", { name: /Members/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "members-desktop.png"), fullPage: false });

    // 3. Files
    await page.getByRole("link", { name: /^Files$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/files/);
    await expect(page.getByRole("heading", { name: /Files/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "files-desktop.png"), fullPage: false });

    // 4. Audit (free plan, export locked)
    await page.getByRole("link", { name: /^Audit Logs$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/audit/);
    await expect(page.getByRole("heading", { name: /Audit Logs/i })).toBeVisible();
    await expect(page.getByText("Pro").first()).toBeVisible({ timeout: 10000 });
    const exportBtn = page.getByRole("button", { name: /Export CSV/i }).first();
    await expect(exportBtn).toBeVisible();
    await exportBtn.click();
    await expect(page.getByText(/Upgrade Required/i)).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "audit-free-locked-desktop.png"), fullPage: false });
    await page.keyboard.press("Escape");
    await expect(page.getByText(/Upgrade Required/i)).not.toBeVisible();

    // 5. Billing
    await page.getByRole("link", { name: /^Billing & Plans$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/billing/);
    await expect(page.getByRole("heading", { name: /Billing/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "billing-desktop.png"), fullPage: false });

    // 6. Platform
    await page.goto("/platform");
    await expect(page.getByRole("heading", { name: /Platform/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "platform-desktop.png"), fullPage: false });
  });

  test("capture mobile (390px) screenshots", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    // Login and launch demo
    await page.goto("/login");
    const demoButton = page.getByRole("button", { name: /Explore Interactive Demo/i });
    await expect(demoButton).toBeVisible();
    await demoButton.click();

    await page.waitForURL(/\/o\/[a-f0-9-]+\/overview/, { timeout: 15000 });
    const currentUrl = page.url();
    const orgIdMatch = currentUrl.match(/\/o\/([a-f0-9-]+)\/overview/);
    expect(orgIdMatch).not.toBeNull();
    const orgId = orgIdMatch![1];

    // 1. Mobile Overview
    await expect(page.getByRole("heading", { name: /Overview/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "overview-mobile.png"), fullPage: false });

    // 2. Mobile Members
    await page.getByRole("link", { name: /^Members$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/members/);
    await expect(page.getByRole("heading", { name: /Members/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "members-mobile.png"), fullPage: false });

    // 3. Mobile Files
    await page.getByRole("link", { name: /^Files$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/files/);
    await expect(page.getByRole("heading", { name: /Files/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "files-mobile.png"), fullPage: false });

    // 4. Mobile Audit (free plan, export locked)
    await page.getByRole("link", { name: /^Audit Logs$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/audit/);
    await expect(page.getByRole("heading", { name: /Audit Logs/i })).toBeVisible();
    await expect(page.getByText("Pro").first()).toBeVisible({ timeout: 10000 });
    const exportBtnMobile = page.getByRole("button", { name: /Export CSV/i }).first();
    await expect(exportBtnMobile).toBeVisible();
    await exportBtnMobile.click();
    await expect(page.getByText(/Upgrade Required/i)).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "audit-free-locked-mobile.png"), fullPage: false });
    await page.keyboard.press("Escape");
    await expect(page.getByText(/Upgrade Required/i)).not.toBeVisible();

    // 5. Mobile Billing
    await page.getByRole("link", { name: /^Billing & Plans$/i }).click();
    await page.waitForURL(/\/o\/[a-f0-9-]+\/billing/);
    await expect(page.getByRole("heading", { name: /Billing/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "billing-mobile.png"), fullPage: false });

    // 6. Mobile Platform
    await page.goto("/platform");
    await expect(page.getByRole("heading", { name: /Platform/i })).toBeVisible();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screensDir, "platform-mobile.png"), fullPage: false });
  });
});
