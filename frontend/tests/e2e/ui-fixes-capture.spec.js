import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, "results", "ui-fixes");

async function login(page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("commander");
  await page.getByLabel("Password").fill("commander");
  await page.getByRole("button", { name: /Sign in to Command Center/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
}

async function fontAudit(page) {
  return page.evaluate(() => {
    const body = window.getComputedStyle(document.body).fontSize;
    const tableCell = document.querySelector(".ops-table tbody td");
    return {
      body,
      tableCell: tableCell ? window.getComputedStyle(tableCell).fontSize : null,
    };
  });
}

test.describe("UI fixes capture", () => {
  // Individual expects below wait up to 120s (optimizer + routing on the full
  // dataset), so the test budget has to exceed that or Firefox times out first.
  test.describe.configure({ timeout: 180000 });

  test.beforeAll(() => {
    fs.mkdirSync(OUT, { recursive: true });
  });

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await login(page);
  });

  test("1 typography audit screenshots", async ({ page }) => {
    const pages = [
      { route: "/dashboard", name: "dashboard" },
      { route: "/resources", name: "resources" },
      { route: "/zones", name: "zones" },
      { route: "/missions", name: "missions" },
      { route: "/teams", name: "teams" },
      { route: "/ai-demand", name: "ai-demand" },
    ];

    for (const entry of pages) {
      await page.goto(entry.route, { waitUntil: "networkidle" });
      await expect(page.locator("main, .ops-page, [class*='ops-']").first()).toBeVisible({ timeout: 30000 });
      await page.waitForTimeout(800);
      const fonts = await fontAudit(page);
      expect(parseFloat(fonts.body)).toBeGreaterThanOrEqual(16);
      if (fonts.tableCell) {
        expect(parseFloat(fonts.tableCell)).toBeGreaterThanOrEqual(15);
      }
      await page.screenshot({
        path: path.join(OUT, `1-typography-${entry.name}.png`),
        fullPage: true,
      });
    }
  });

  test("2 operations map size and fullscreen", async ({ page }) => {
    await page.goto("/operations");
    await expect(page.getByRole("heading", { name: "Resource Allocation" })).toBeVisible({
      timeout: 60000,
    });
    await page.getByRole("button", { name: "Run Optimization" }).click();
    await expect(page.getByText(/Coverage:/)).toBeVisible({ timeout: 120000 });
    await page.getByRole("button", { name: "Generate Route" }).click();
    const routeHeading = page.getByRole("heading", { name: "Route Overlay" });
    await expect(routeHeading).toBeVisible({ timeout: 120000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(OUT, "2-operations-map-large.png"), fullPage: true });

    await page.getByRole("button", { name: "Fullscreen map" }).click();
    await expect(page.locator(".leaflet-container")).toBeVisible();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, "2-operations-map-fullscreen.png"), fullPage: true });
  });

  test("3 resources filters", async ({ page }) => {
    await page.goto("/resources");
    await expect(page.getByRole("heading", { name: "Search & Filters" })).toBeVisible({
      timeout: 60000,
    });
    const categorySelect = page.locator(".ops-card").first().locator("select").nth(1);
    await categorySelect.selectOption({ index: 1 });
    await page.screenshot({ path: path.join(OUT, "3-resources-filters.png"), fullPage: true });
  });

  test("4 satellite without coverage note", async ({ page }) => {
    await page.goto("/satellite");
    await expect(page.getByRole("heading", { name: "Assessment" })).toBeVisible({ timeout: 60000 });
    await expect(page.getByText(/outside imported Copernicus EMS coverage/i)).toHaveCount(0);
    await page.screenshot({ path: path.join(OUT, "4-satellite-clean.png"), fullPage: true });
  });
});
