import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = path.join(__dirname, "results");
const SCREENSHOTS_DIR = path.join(RESULTS_DIR, "screenshots");
const API_URL = process.env.PLAYWRIGHT_API_URL || "http://127.0.0.1:8000";
const COMMANDER_USERNAME = process.env.PLAYWRIGHT_COMMANDER_USERNAME || "commander";
const COMMANDER_PASSWORD = process.env.PLAYWRIGHT_COMMANDER_PASSWORD || "commander";

const BENIGN_CONSOLE_PATTERNS = [
  /favicon/i,
  /Failed to load resource.*404/i,
  // In-flight fetches aborted by navigation, one spelling per engine.
  /net::ERR_FAILED/i,
  /net::ERR_ABORTED/i,
  /NetworkError when attempting to fetch resource/i,
  /The operation was aborted/i,
  /Load failed/i,
  /Download the React DevTools/i,
  /\[vite\]/i,
  /access control checks/i,
];

function isBenignConsoleMessage(text) {
  return BENIGN_CONSOLE_PATTERNS.some((pattern) => pattern.test(text));
}

/**
 * Real credentials are required: apiRequest() hard-redirects to "/" on any
 * 401, so a stub token would bounce every protected page back to the landing.
 */
async function login(request) {
  const response = await request.post(`${API_URL}/auth/login`, {
    data: {
      username: COMMANDER_USERNAME,
      password: COMMANDER_PASSWORD,
    },
  });
  expect(response.ok(), `Login failed: ${response.status()}`).toBeTruthy();
  const body = await response.json();
  return {
    token: body.access_token,
    user: { username: body.username, role: body.role },
  };
}

async function fetchDashboardMetrics(request, token) {
  const response = await request.get(`${API_URL}/analytics/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok(), `Dashboard API failed: ${response.status()}`).toBeTruthy();
  return response.json();
}

async function installAuthSession(page, session) {
  await page.addInitScript(
    ([token, user]) => {
      localStorage.setItem("disaster_access_token", token);
      localStorage.setItem("disaster_auth_user", JSON.stringify(user));
    },
    [session.token, session.user],
  );
}

async function signInFromLanding(page, session) {
  await installAuthSession(page, session);
  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
}

async function countGridColumns(page, gridSelector) {
  const cards = page.locator(`${gridSelector} > div`);
  const count = await cards.count();
  if (count === 0) return 0;

  const xs = new Set();
  for (let i = 0; i < count; i += 1) {
    const box = await cards.nth(i).boundingBox();
    if (box) xs.add(Math.round(box.x));
  }
  return xs.size;
}

async function saveScreenshot(page, browserName, name) {
  const dir = path.join(SCREENSHOTS_DIR, browserName);
  fs.mkdirSync(dir, { recursive: true });
  const filePath = path.join(dir, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

test.describe("Cross-browser disaster response smoke", () => {
  /** @type {import('@playwright/test').ConsoleMessage[]} */
  let consoleErrors;
  /** @type {Record<string, unknown>} */
  let apiMetrics;
  /** @type {Record<string, unknown>} */
  const observations = {};
  /** @type {{ token: string, user: { username: string, role: string } }} */
  let session;

  test.beforeAll(async ({ request }) => {
    session = await login(request);
    apiMetrics = await fetchDashboardMetrics(request, session.token);
  });

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    page.on("console", async (msg) => {
      if (msg.type() !== "error") return;
      let text = msg.text();
      // Firefox renders object args as "JSHandle@object"; resolve them so the
      // failure message is actually readable.
      if (text.includes("JSHandle@")) {
        const parts = await Promise.all(
          msg.args().map((arg) =>
            arg
              .evaluate((v) => {
                if (v instanceof Error) {
                  return `${v.name}: ${v.message}\n${v.stack || ""}`;
                }
                if (v && typeof v === "object") {
                  try {
                    return JSON.stringify(v);
                  } catch {
                    return Object.prototype.toString.call(v);
                  }
                }
                return String(v);
              })
              .catch(() => "[unserializable]"),
          ),
        );
        // Args only fail to resolve when the execution context was torn down
        // mid-navigation, which is the same abort artifact as above.
        if (parts.length > 0 && parts.every((p) => p === "[unserializable]")) {
          return;
        }
        text = parts.join(" ") || text;
      }
      if (!isBenignConsoleMessage(text)) {
        consoleErrors.push(text);
      }
    });
    page.on("pageerror", (err) => {
      const text = `pageerror: ${err.message}`;
      if (!isBenignConsoleMessage(text)) {
        consoleErrors.push(text);
      }
    });
  });

  test("dashboard, navigation, responsive layout, console health", async ({ page, browserName }) => {
    test.setTimeout(180_000);

    await page.goto("/", { waitUntil: "domcontentloaded" });
    await signInFromLanding(page, session);

    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { name: "Disaster Response Command Center" })).toBeVisible({
      timeout: 30_000,
    });

    const activeZonesButton = main.getByRole("button", { name: /Active Zones/i });
    const stockButton = main.getByRole("button", { name: /Available Stock/i });
    const activeZonesValue = activeZonesButton.getByTestId("stat-value");
    const stockValue = stockButton.getByTestId("stat-value");

    await expect(activeZonesButton).toBeVisible({ timeout: 30_000 });
    await expect(stockButton).toBeVisible({ timeout: 30_000 });

    await expect(activeZonesValue).toHaveText(String(apiMetrics.active_zones), {
      timeout: 120_000,
    });
    await expect(stockValue).toHaveText(String(apiMetrics.available_resources), {
      timeout: 120_000,
    });

    observations[`${browserName}:dashboard`] = {
      active_zones_ui: await activeZonesButton.innerText(),
      available_stock_ui: await stockButton.innerText(),
      api_active_zones: apiMetrics.active_zones,
      api_available_resources: apiMetrics.available_resources,
    };

    await saveScreenshot(page, browserName, "01-dashboard-desktop");

    const sidebarNav = [
      { linkName: "Allocation", heading: "Resource Allocation", slug: "operations" },
      { linkName: "Zones", heading: "Disaster Zones", slug: "zones" },
      { linkName: "Resources", heading: "Resources & Depots", slug: "resources" },
      { linkName: "Missions", heading: "Mission Operations", slug: "missions" },
    ];

    const responsiveTargets = [
      { slug: "dashboard", heading: "Disaster Response Command Center", path: "/dashboard" },
      ...sidebarNav.map((item) => ({
        slug: item.slug,
        heading: item.heading,
        path: `/${item.slug}`,
      })),
    ];

    const responsiveViewports = [
      { name: "375px-phone", width: 375, height: 812 },
      { name: "768px-tablet", width: 768, height: 1024 },
      { name: "1024px-laptop", width: 1024, height: 900 },
    ];

    for (const viewport of responsiveViewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.waitForTimeout(300);

      for (const target of responsiveTargets) {
        await page.goto(target.path, { waitUntil: "domcontentloaded" });
        await expect(main.getByRole("heading", { name: target.heading })).toBeVisible({
          timeout: 45_000,
        });
        await saveScreenshot(page, browserName, `${viewport.name}-${target.slug}`);
      }

      if (viewport.width < 768) {
        await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
        await page.getByRole("button", { name: "Open navigation menu" }).click();
        await expect(page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name: "Zones" })).toBeVisible();
        await saveScreenshot(page, browserName, `${viewport.name}-mobile-nav-open`);
        await page.getByRole("button", { name: "Close navigation menu" }).click();
      }
    }

    // Scope to the desktop rail: the mobile drawer carries the same
    // "Main menu" label. Hovering settles the collapse animation first, which
    // also swaps each link's name from aria-label to its text.
    const desktopSidebar = page.locator("aside.hidden.md\\:flex");
    const mainNav = desktopSidebar.getByRole("navigation", { name: "Main menu" });

    async function clickNav(linkName) {
      await desktopSidebar.hover();
      const link = mainNav.getByRole("link", { name: linkName, exact: true });
      await expect(link, `sidebar link "${linkName}" should be present`).toBeVisible({
        timeout: 15_000,
      });
      await link.click();
    }

    for (const target of sidebarNav) {
      await clickNav(target.linkName);
      await expect(main.getByRole("heading", { name: target.heading })).toBeVisible({
        timeout: 45_000,
      });
      await saveScreenshot(page, browserName, `02-${target.slug}`);
    }

    await clickNav("Dashboard");
    await expect(main.getByRole("heading", { name: "Disaster Response Command Center" })).toBeVisible({
      timeout: 45_000,
    });

    await page.setViewportSize({ width: 1024, height: 900 });
    await page.waitForTimeout(500);

    // Stable hook: the previous class-string selector broke whenever the
    // grid's utility classes changed.
    const statGridSelector = '[data-testid="kpi-grid"]';
    const colsAt1024 = await countGridColumns(page, statGridSelector);
    const sidebar = page.locator("aside").first();
    const sidebarBox1024 = await sidebar.boundingBox();
    observations[`${browserName}:layout_1024`] = {
      stat_card_columns: colsAt1024,
      sidebar_width_px: sidebarBox1024?.width ?? null,
    };

    await page.setViewportSize({ width: 1400, height: 900 });
    await page.waitForTimeout(500);

    const colsAt1400 = await countGridColumns(page, statGridSelector);
    observations[`${browserName}:layout_1400`] = { stat_card_columns: colsAt1400 };

    await saveScreenshot(page, browserName, "04-dashboard-1400px");

    // The KPI grid now breaks to 4 columns at md (768px), so common laptop
    // widths no longer render a half-empty 2x2.
    expect(colsAt1024, `${browserName}: expected 4 stat columns at 1024px`).toBe(4);
    expect(colsAt1400, `${browserName}: expected 4 stat columns at 1400px`).toBe(4);

    fs.mkdirSync(RESULTS_DIR, { recursive: true });
    fs.writeFileSync(
      path.join(RESULTS_DIR, `observations-${browserName}.json`),
      JSON.stringify(observations, null, 2),
    );

    if (consoleErrors.length > 0) {
      throw new Error(`Console errors on ${browserName}:\n${consoleErrors.join("\n")}`);
    }
  });
});
