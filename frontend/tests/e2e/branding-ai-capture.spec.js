import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "results", "branding-ai");
const API_URL = process.env.VITE_API_URL || "http://127.0.0.1:8000";

test("capture branding and AI visibility screenshots", async ({ page, request }) => {
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

  await page.goto("/dashboard", { waitUntil: "networkidle" });
  await expect(page.getByText("DRMS Command Center").first()).toBeVisible();
  await expect(page.getByTestId("ai-demand-insight")).toBeVisible();
  await page.screenshot({
    path: path.join(OUT_DIR, "dashboard-branding-ai.png"),
    fullPage: true,
  });

  await page.goto("/operations", { waitUntil: "networkidle" });
  await expect(page.getByText("AI-recommended allocation")).toBeVisible();
  await page.screenshot({
    path: path.join(OUT_DIR, "operations-ai-label.png"),
    fullPage: true,
  });
});
