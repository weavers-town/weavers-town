import { expect, test } from "@playwright/test";
import { promises as fs } from "node:fs";
import path from "node:path";

const workspaceRoot = path.resolve(__dirname, "..");
const publicDir = path.join(workspaceRoot, "public");

async function collectHtmlFiles(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        return collectHtmlFiles(fullPath);
      }
      if (entry.isFile() && entry.name.endsWith(".html")) {
        return [fullPath];
      }
      return [];
    }),
  );

  return files.flat();
}

function toRoute(htmlFile: string): string {
  const rel = path.relative(publicDir, htmlFile).replaceAll(path.sep, "/");
  if (rel === "index.html") {
    return "/";
  }
  if (rel.endsWith("/index.html")) {
    return `/${rel.slice(0, -"/index.html".length)}/`;
  }
  return `/${rel}`;
}

function normalizeLink(link: string, fromRoute: string): string | null {
  if (!link || link.startsWith("#")) {
    return null;
  }
  if (link.startsWith("mailto:") || link.startsWith("tel:") || link.startsWith("javascript:")) {
    return null;
  }

  const base = new URL(`http://127.0.0.1:4173${fromRoute}`);
  const url = new URL(link, base);

  if (url.origin !== base.origin) {
    return null;
  }

  return `${url.pathname}${url.search}`;
}

test("all generated html pages return content", async ({ request }) => {
  const htmlFiles = await collectHtmlFiles(publicDir);
  const routes = Array.from(new Set(htmlFiles.map(toRoute))).sort();

  expect(routes.length, "expected to find many generated routes in public/").toBeGreaterThan(10);

  for (const route of routes) {
    const response = await request.get(route);
    expect(response.status(), `${route} should return HTTP 200`).toBe(200);

    const contentType = response.headers()["content-type"] || "";
    expect(contentType, `${route} should be served as html`).toContain("text/html");

    const html = await response.text();
    expect(html, `${route} should include a title tag`).toMatch(/<title>\s*[^<]+\s*<\/title>/i);
    const text = html
      .replace(/<script[\s\S]*?<\/script>/gi, " ")
      .replace(/<style[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    expect(text.length, `${route} should include meaningful text`).toBeGreaterThan(80);
    expect(text, `${route} should not include todo placeholders`).not.toMatch(/\bTODO\b|lorem ipsum/i);
  }
});

test("all internal page links resolve", async ({ request }) => {
  const htmlFiles = await collectHtmlFiles(publicDir);
  const routes = Array.from(new Set(htmlFiles.map(toRoute))).sort();
  const linksToCheck = new Set<string>();

  for (const route of routes) {
    const response = await request.get(route);
    expect(response.status(), `${route} should return HTTP 200`).toBe(200);

    const html = await response.text();
    const hrefMatches = html.matchAll(/href\s*=\s*["']([^"']+)["']/gi);
    for (const match of hrefMatches) {
      const href = match[1]?.trim();
      if (!href) {
        continue;
      }
      const normalized = normalizeLink(href, route);
      if (normalized) {
        linksToCheck.add(normalized);
      }
    }
  }

  for (const link of Array.from(linksToCheck).sort()) {
    const response = await request.get(link);
    expect(response.status(), `${link} should resolve`).toBeLessThan(400);
  }
});