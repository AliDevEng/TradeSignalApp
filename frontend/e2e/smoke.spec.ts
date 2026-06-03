import { expect, test } from "@playwright/test";

/**
 * Key-route smoke tests. These assert the app shell renders and core routes are
 * reachable; they run against the typed mock fallback when no backend is up, so
 * they stay deterministic in CI without a live API.
 */

test("dashboard renders the command center", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: /open command palette/i })).toBeVisible();
});

test("signals route lists setups", async ({ page }) => {
  await page.goto("/signals");
  await expect(page.getByRole("heading", { name: "Signals", level: 1 })).toBeVisible();
});

test("analysis route shows the run ledger", async ({ page }) => {
  await page.goto("/analysis");
  await expect(page.getByRole("heading", { name: "Analysis Runs", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: /trigger analysis run/i })).toBeVisible();
});

test("pair detail route renders", async ({ page }) => {
  await page.goto("/pairs/XAUUSD");
  await expect(page.getByRole("heading", { name: "XAUUSD", level: 1 })).toBeVisible();
});

test("command palette opens with the keyboard and searches", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Control+k");
  const dialog = page.getByRole("dialog", { name: /command palette/i });
  await expect(dialog).toBeVisible();
  await page.getByPlaceholder(/search pairs/i).fill("analysis");
  await expect(dialog.getByText("Analysis Runs")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("unknown route renders the not-found page", async ({ page }) => {
  const response = await page.goto("/this-route-does-not-exist");
  expect(response?.status()).toBe(404);
});
