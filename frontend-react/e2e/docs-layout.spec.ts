import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screensDir = path.resolve(__dirname, "../../docs/screens");

test.describe("Docs Layout & Responsive Viewport Verification", () => {
  test("/docs/search layout at 1440px (desktop) and 390px (mobile)", async ({ page }) => {
    // 1. Desktop Viewport (1440px)
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/docs/search");
    await page.waitForLoadState("networkidle");

    // Assert h1 is visible and matches heading scale
    const h1Desktop = page.getByRole("heading", { level: 1, name: "Search Architecture & Indexing" });
    await expect(h1Desktop).toBeVisible();

    // Assert status badge is visible
    const badgeDesktop = page.getByTestId("docs-status-badge");
    await expect(badgeDesktop).toBeVisible();
    await expect(badgeDesktop).toHaveText(/Paid feature, not enabled on this deployment|Active on this deployment/);

    // Assert desktop "On this page" TOC is visible
    await expect(page.getByText("On this page")).toBeVisible();

    // Assert no horizontal scroll on desktop
    const overflowDesktop = await page.evaluate(() => {
      const el = document.scrollingElement || document.documentElement;
      return el.scrollWidth <= window.innerWidth;
    });
    expect(overflowDesktop).toBe(true);

    // Save After Desktop Screenshot
    await page.screenshot({ path: path.join(screensDir, "docs-search-after-desktop.png"), fullPage: true });

    // 2. Mobile Viewport (390px)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/docs/search");
    await page.waitForLoadState("networkidle");

    // Assert h1 is visible on mobile
    const h1Mobile = page.getByRole("heading", { level: 1, name: "Search Architecture & Indexing" });
    await expect(h1Mobile).toBeVisible();

    // Assert status badge is visible on mobile
    const badgeMobile = page.getByTestId("docs-status-badge");
    await expect(badgeMobile).toBeVisible();

    // Assert TOC is hidden on mobile (< 1024px)
    await expect(page.getByText("On this page")).not.toBeVisible();

    // Assert strict zero horizontal scroll on mobile viewport
    const overflowMobile = await page.evaluate(() => {
      const el = document.scrollingElement || document.documentElement;
      return el.scrollWidth <= window.innerWidth;
    });
    expect(overflowMobile).toBe(true);

    // Save After Mobile Screenshot
    await page.screenshot({ path: path.join(screensDir, "docs-search-after-mobile.png"), fullPage: true });
  });

  test("/docs/email layout at 1440px (desktop) and 390px (mobile)", async ({ page }) => {
    // 1. Desktop Viewport (1440px)
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/docs/email");
    await page.waitForLoadState("networkidle");

    // Assert h1 is visible
    const h1Desktop = page.getByRole("heading", { level: 1, name: "Email Delivery Architecture" });
    await expect(h1Desktop).toBeVisible();

    // Assert status badge is visible
    const badgeDesktop = page.getByTestId("docs-status-badge");
    await expect(badgeDesktop).toBeVisible();
    await expect(badgeDesktop).toHaveText(/Paid feature, not enabled on this deployment|Active on this deployment/);

    // Assert desktop "On this page" TOC is visible
    await expect(page.getByText("On this page")).toBeVisible();

    // Assert no horizontal scroll on desktop
    const overflowDesktop = await page.evaluate(() => {
      const el = document.scrollingElement || document.documentElement;
      return el.scrollWidth <= window.innerWidth;
    });
    expect(overflowDesktop).toBe(true);

    // Save After Desktop Screenshot
    await page.screenshot({ path: path.join(screensDir, "docs-email-after-desktop.png"), fullPage: true });

    // 2. Mobile Viewport (390px)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/docs/email");
    await page.waitForLoadState("networkidle");

    // Assert h1 is visible on mobile
    const h1Mobile = page.getByRole("heading", { level: 1, name: "Email Delivery Architecture" });
    await expect(h1Mobile).toBeVisible();

    // Assert status badge is visible on mobile
    const badgeMobile = page.getByTestId("docs-status-badge");
    await expect(badgeMobile).toBeVisible();

    // Assert TOC is hidden on mobile (< 1024px)
    await expect(page.getByText("On this page")).not.toBeVisible();

    // Assert strict zero horizontal scroll on mobile viewport
    const overflowMobile = await page.evaluate(() => {
      const el = document.scrollingElement || document.documentElement;
      return el.scrollWidth <= window.innerWidth;
    });
    expect(overflowMobile).toBe(true);

    // Save After Mobile Screenshot
    await page.screenshot({ path: path.join(screensDir, "docs-email-after-mobile.png"), fullPage: true });
  });
});
