import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "results", "bugfix-pass");
const API_URL = process.env.VITE_API_URL || "http://127.0.0.1:8000";

async function login(request) {
  const response = await request.post(`${API_URL}/auth/login`, {
    data: { username: "commander", password: "commander" },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  return {
    token: body.access_token,
    user: { username: body.username, role: body.role },
  };
}

test("capture four bugfix screenshots", async ({ page, request }) => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const session = await login(request);

  await page.addInitScript(
    ([token, user]) => {
      localStorage.setItem("disaster_access_token", token);
      localStorage.setItem("disaster_auth_user", JSON.stringify(user));
    },
    [session.token, session.user],
  );

  await page.setViewportSize({ width: 1024, height: 900 });

  // 1 & 2 & 3 — Dashboard: AI sync, sidebar/summary overflow, chart fill
  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await expect(page.getByTestId("ai-demand-insight")).toBeVisible();

  const incidentSelect = page.getByLabel("Select incident");
  await incidentSelect.selectOption({ index: 0 });
  await page.waitForTimeout(800);
  const firstZoneText = await page.getByTestId("ai-demand-insight").innerText();
  await page.screenshot({
    path: path.join(OUT_DIR, "1-ai-linked-first-incident.png"),
    fullPage: true,
  });

  const optionCount = await incidentSelect.locator("option").count();
  if (optionCount > 1) {
    await incidentSelect.selectOption({ index: 1 });
    await page.waitForTimeout(1200);
    await page.screenshot({
      path: path.join(OUT_DIR, "1-ai-linked-second-incident.png"),
      fullPage: true,
    });
  }

  await page.screenshot({
    path: path.join(OUT_DIR, "2-sidebar-summary-wrap.png"),
    fullPage: false,
  });

  // Expanded sidebar branding (desktop)
  const collapseBtn = page.getByRole("button", { name: /Collapse sidebar|Pin sidebar open/i });
  if (await collapseBtn.isVisible()) {
    await collapseBtn.click();
    await page.waitForTimeout(300);
    await page.screenshot({
      path: path.join(OUT_DIR, "2-sidebar-expanded-branding.png"),
      fullPage: false,
    });
  }

  await page.locator("text=Inventory by Category").scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await page.screenshot({
    path: path.join(OUT_DIR, "3-chart-fills-container.png"),
    fullPage: false,
  });

  // 4 — Search input spacing on Zones
  await page.goto("/zones", { waitUntil: "networkidle" });
  await page.locator('input[type="search"]').first().scrollIntoViewIfNeeded();
  await page.screenshot({
    path: path.join(OUT_DIR, "4-search-input-spacing.png"),
    fullPage: false,
  });
});
