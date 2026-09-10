import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RESULTS_DIR = path.join(__dirname, "results", "responsive");
const SCREENSHOTS_DIR = path.join(RESULTS_DIR, "screenshots");
const REPORT_PATH = path.join(RESULTS_DIR, "RESPONSIVE_AUDIT_REPORT.md");

const COMMANDER_USERNAME = process.env.PLAYWRIGHT_COMMANDER_USERNAME || "commander";
const COMMANDER_PASSWORD = process.env.PLAYWRIGHT_COMMANDER_PASSWORD || "commander";

const VIEWPORTS = [
  { name: "375px-phone", width: 375, height: 812 },
  { name: "768px-tablet", width: 768, height: 1024 },
  { name: "1024px-laptop", width: 1024, height: 900 },
];

const PAGES = [
  { slug: "dashboard", path: "/dashboard", heading: "Disaster Response Command Center" },
  { slug: "operations", path: "/operations", heading: "Resource Allocation" },
  { slug: "zones", path: "/zones", heading: "Disaster Zones" },
  { slug: "resources", path: "/resources", heading: "Resources & Depots" },
  { slug: "missions", path: "/missions", heading: "Mission Operations" },
];

const API_URL = process.env.VITE_API_URL || "http://127.0.0.1:8000";

let cachedSession = null;

/**
 * Obtain a real token. A stub token is not usable: apiRequest() hard-redirects
 * to "/" on any 401, so every protected endpoint must genuinely authenticate.
 */
async function getSession(request) {
  if (cachedSession) return cachedSession;
  const response = await request.post(`${API_URL}/auth/login`, {
    data: { username: COMMANDER_USERNAME, password: COMMANDER_PASSWORD },
  });
  if (!response.ok()) {
    throw new Error(
      `Login failed (${response.status()}). Backend must be reachable at ${API_URL}.`,
    );
  }
  const body = await response.json();
  cachedSession = {
    token: body.access_token,
    user: { username: body.username, role: body.role },
  };
  return cachedSession;
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

async function saveScreenshot(page, viewportName, pageSlug) {
  const dir = path.join(SCREENSHOTS_DIR, viewportName);
  fs.mkdirSync(dir, { recursive: true });
  const filePath = path.join(dir, `${pageSlug}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

/**
 * Detect layout issues: document/body horizontal overflow, elements clipped
 * outside the viewport, and interactive controls partially off-screen.
 */
async function auditLayout(page, viewportWidth) {
  return page.evaluate((vw) => {
    const issues = [];
    const doc = document.documentElement;
    const body = document.body;

    const docOverflow = doc.scrollWidth - doc.clientWidth;
    const bodyOverflow = body.scrollWidth - body.clientWidth;
    if (docOverflow > 2) {
      issues.push({
        type: "horizontal-scroll",
        detail: `document scrollWidth ${doc.scrollWidth}px exceeds clientWidth ${doc.clientWidth}px by ${docOverflow}px`,
      });
    }
    if (bodyOverflow > 2) {
      issues.push({
        type: "horizontal-scroll",
        detail: `body scrollWidth ${body.scrollWidth}px exceeds clientWidth ${body.clientWidth}px by ${bodyOverflow}px`,
      });
    }

    // Content inside a horizontally scrollable ancestor is reachable by
    // scrolling that container, so it is not layout breakage. Only page-level
    // overflow (reported separately above) counts.
    const inScrollableX = (el) => {
      let node = el.parentElement;
      while (node && node !== document.body) {
        const s = window.getComputedStyle(node);
        if (
          (s.overflowX === "auto" || s.overflowX === "scroll") &&
          node.scrollWidth > node.clientWidth + 1
        ) {
          return true;
        }
        node = node.parentElement;
      }
      return false;
    };

    const viewportRight = vw;
    const selectors = [
      "header",
      "aside",
      "main",
      "main h1",
      "main button",
      "main a",
      "main table",
      ".ops-card",
    ];

    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        const tag = el.tagName.toLowerCase();
        // The closed mobile drawer is parked off-canvas by design.
        if (tag === "aside" && el.getAttribute("aria-hidden") === "true") {
          continue;
        }
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        if (style.display === "none" || style.visibility === "hidden" || rect.width === 0) {
          continue;
        }
        if (inScrollableX(el)) {
          continue;
        }

        const label =
          el.getAttribute("aria-label") ||
          el.textContent?.trim().slice(0, 40) ||
          selector;

        if (rect.right > viewportRight + 2) {
          issues.push({
            type: "overflow-right",
            detail: `<${tag}> "${label}" extends ${Math.round(rect.right - viewportRight)}px past viewport (${Math.round(rect.right)}px > ${vw}px)`,
          });
        }
        if (rect.left < -2) {
          issues.push({
            type: "overflow-left",
            detail: `<${tag}> "${label}" starts ${Math.round(-rect.left)}px left of viewport`,
          });
        }

        if (tag === "button" || (tag === "a" && el.classList.contains("ops-btn"))) {
          const visibleWidth = Math.min(rect.right, viewportRight) - Math.max(rect.left, 0);
          if (visibleWidth > 0 && visibleWidth < rect.width * 0.85) {
            issues.push({
              type: "button-clipped",
              detail: `Button "${label}" only ${Math.round(visibleWidth)}px of ${Math.round(rect.width)}px visible`,
            });
          }
        }
      }
    }

    const main = document.querySelector("main");
    const aside = document.querySelector("aside");
    if (main && aside) {
      const mainRect = main.getBoundingClientRect();
      const asideRect = aside.getBoundingClientRect();
      if (mainRect.width < 200) {
        issues.push({
          type: "narrow-main",
          detail: `Main content area only ${Math.round(mainRect.width)}px wide (sidebar ${Math.round(asideRect.width)}px)`,
        });
      }
      if (asideRect.width > vw * 0.45 && vw <= 768) {
        issues.push({
          type: "sidebar-too-wide",
          detail: `Sidebar ${Math.round(asideRect.width)}px consumes ${Math.round((asideRect.width / vw) * 100)}% of ${vw}px viewport`,
        });
      }
    }

    const deduped = [];
    const seen = new Set();
    for (const issue of issues) {
      const key = `${issue.type}:${issue.detail}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(issue);
      }
    }
    return deduped;
  }, viewportWidth);
}

test.describe("Responsive layout audit", () => {
  test.beforeEach(async ({ page, request }) => {
    await installAuthSession(page, await getSession(request));
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(
      page.getByRole("main").getByRole("heading", { name: "Disaster Response Command Center" }),
    ).toBeVisible({ timeout: 60_000 });
  });

  for (const viewport of VIEWPORTS) {
    test(`${viewport.name} — dashboard, operations, zones, resources, missions`, async ({ page }) => {
      test.setTimeout(240_000);

      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      const allIssues = {};

      for (const target of PAGES) {
        await page.goto(target.path, { waitUntil: "domcontentloaded" });
        await expect(page.getByRole("main").getByRole("heading", { name: target.heading })).toBeVisible({
          timeout: 45_000,
        });
        await page.waitForTimeout(600);

        const screenshot = await saveScreenshot(page, viewport.name, target.slug);
        const issues = await auditLayout(page, viewport.width);

        allIssues[target.slug] = { screenshot, issues };

        if (viewport.width < 768) {
          await expect(page.getByRole("button", { name: "Open navigation menu" })).toBeVisible();
          await expect(page.locator("aside.hidden.md\\:flex")).toBeHidden();
          await page.getByRole("button", { name: "Open navigation menu" }).click();
          await expect(
            page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name: "Zones" }),
          ).toBeVisible();
          await saveScreenshot(page, viewport.name, `${target.slug}-nav-open`);
          await page.getByRole("button", { name: "Close navigation menu" }).click();
        } else {
          await expect(page.locator("aside.hidden.md\\:flex")).toBeVisible();
        }
      }

      fs.mkdirSync(RESULTS_DIR, { recursive: true });
      fs.writeFileSync(
        path.join(RESULTS_DIR, `audit-${viewport.name}.json`),
        JSON.stringify(allIssues, null, 2),
      );

      const breaking = Object.entries(allIssues).flatMap(([slug, data]) =>
        data.issues.map((issue) => ({ slug, ...issue })),
      );

      if (breaking.length > 0) {
        console.log(`\n=== ${viewport.name} layout issues ===`);
        for (const item of breaking) {
          console.log(`  [${item.slug}] ${item.type}: ${item.detail}`);
        }
      }

      // Soft per page, so one broken page still reports the state of the rest.
      for (const [slug, data] of Object.entries(allIssues)) {
        const genuine = data.issues.filter(
          (i) =>
            i.type === "horizontal-scroll" ||
            i.type === "button-clipped" ||
            i.type === "overflow-right",
        );
        expect
          .soft(genuine, `${viewport.name} / ${slug}: genuine layout breakage`)
          .toEqual([]);
      }
    });
  }

  test.afterAll(async () => {
    const lines = ["# Responsive layout audit", "", `Generated: ${new Date().toISOString()}`, ""];

    for (const viewport of VIEWPORTS) {
      const auditPath = path.join(RESULTS_DIR, `audit-${viewport.name}.json`);
      if (!fs.existsSync(auditPath)) continue;

      const data = JSON.parse(fs.readFileSync(auditPath, "utf8"));
      lines.push(`## ${viewport.name}`, "");

      for (const target of PAGES) {
        const entry = data[target.slug];
        if (!entry) continue;
        lines.push(`### ${target.slug}`, "");
        lines.push(`![${target.slug}](screenshots/${viewport.name}/${target.slug}.png)`, "");
        if (entry.issues.length === 0) {
          lines.push("No layout issues detected.", "");
        } else {
          for (const issue of entry.issues) {
            lines.push(`- **${issue.type}**: ${issue.detail}`);
          }
          lines.push("");
        }
      }
    }

    fs.mkdirSync(RESULTS_DIR, { recursive: true });
    fs.writeFileSync(REPORT_PATH, lines.join("\n"));
  });
});
