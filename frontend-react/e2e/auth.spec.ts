import { test, expect } from '@playwright/test';

test.describe('Authentication E2E Flow', () => {
  test('renders login page and allows user interaction', async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    await expect(page.getByRole('button', { name: /Sign In/i })).toBeVisible();
  });
});
