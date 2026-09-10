import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "results", "design-fixes");
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

async function authGoto(page, request, url) {
  const session = await login(request);
  await page.addInitScript(
    ([token, user]) => {
      localStorage.setItem("disaster_access_token", token);
      localStorage.setItem("disaster_auth_user", JSON.stringify(user));
    },
    [session.token, session.user],
  );
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(url, { waitUntil: "networkidle" });
}

function shot(name) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  return path.join(OUT_DIR, `${name}.png`);
}

test("capture density pages", async ({ page, request }) => {
  await authGoto(page, request, "/disasters");
  await expect(page.getByRole("heading", { name: "Disaster Events" })).toBeVisible();
  await page.screenshot({ path: shot(process.env.SHOT_PREFIX + "disasters"), fullPage: true });

  await page.goto("/missions", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Mission Operations" })).toBeVisible();
  await page.screenshot({ path: shot(process.env.SHOT_PREFIX + "missions"), fullPage: true });

  await page.goto("/resources", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Resources & Depots" })).toBeVisible();
  await page.screenshot({ path: shot(process.env.SHOT_PREFIX + "resources"), fullPage: true });

  await page.goto("/zones", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Disaster Zones" })).toBeVisible();
  await page.screenshot({ path: shot(process.env.SHOT_PREFIX + "zones"), fullPage: true });
});
