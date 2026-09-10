import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "results", "design-fixes");
const API_URL = process.env.VITE_API_URL || "http://127.0.0.1:8000";

test("capture operations route overlay", async ({ page, request }) => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const login = await request.post(`${API_URL}/auth/login`, {
    data: { username: "commander", password: "commander" },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token, username, role } = await login.json();
  await page.addInitScript(
    ([token, user]) => {
      localStorage.setItem("disaster_access_token", token);
      localStorage.setItem("disaster_auth_user", JSON.stringify(user));
    },
    [access_token, { username, role }],
  );
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/operations", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Resource Allocation" })).toBeVisible();

  await page.getByRole("button", { name: "Run Optimization" }).click();
  await expect(page.getByText("Allocation Plan")).toBeVisible();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: "Generate Route" }).click();
  await expect(page.getByText("Route Overlay")).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(1200);

  const prefix = process.env.SHOT_PREFIX || "3-shot-";
  await page.screenshot({
    path: path.join(OUT_DIR, `${prefix}operations-route.png`),
    fullPage: true,
  });
});
