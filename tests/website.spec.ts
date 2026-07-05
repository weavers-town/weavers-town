import { expect, test } from "@playwright/test";

const corePaths = [
  "/",
  "/book/",
  "/book/toc/",
  "/book/table-of-figures/",
];

test("home page renders key content", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/The Thread/i);
  await expect(page.locator("h1", { hasText: "The Thread" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Read the book/i }).first()).toBeVisible();
});

test("vietnamese home page renders key content", async ({ page }) => {
  await page.goto("/vi/");

  await expect(page).toHaveTitle(/Sợi Chỉ/i);
  await expect(page.locator("h1", { hasText: "Sợi Chỉ" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Đọc sách/i }).first()).toBeVisible();
});

test("language switcher links between locales", async ({ page }) => {
  await page.goto("/book/");
  await page.getByRole("button", { name: "Language" }).click();
  await page.getByRole("menuitem", { name: "Tiếng Việt" }).click();
  await expect(page).toHaveURL(/\/vi\/book\//);
  await expect(page.locator(".lang-switcher__option--active")).toHaveText(/Tiếng Việt/);

  await page.getByRole("button", { name: "Ngôn ngữ" }).click();
  await page.getByRole("menuitem", { name: "English" }).click();
  await expect(page).toHaveURL(/\/book\/$/);
});

test("core pages respond successfully", async ({ request }) => {
  for (const path of corePaths) {
    const response = await request.get(path);
    expect(response.status(), `${path} should return HTTP 200`).toBe(200);

    const contentType = response.headers()["content-type"] || "";
    expect(contentType, `${path} should return html`).toContain("text/html");
  }
});

test("header links point to reachable pages", async ({ page, request }) => {
  await page.goto("/");
  const hrefs = await page
    .locator("header nav a")
    .evaluateAll((links) => links.map((el) => el.getAttribute("href") || "").filter(Boolean));

  for (const href of hrefs) {
    if (href.startsWith("#")) {
      await expect(page.locator(href), `${href} anchor target should exist`).toHaveCount(1);
      continue;
    }

    const response = await request.get(href);
    expect(response.status(), `${href} from header nav should be reachable`).toBeLessThan(400);
  }
});

test("removed standalone routes are no longer published", async ({ request }) => {
  const removedPaths = ["/the-thread.html", "/weavers-way.html", "/glossary.html", "/about.html"];

  for (const path of removedPaths) {
    const response = await request.get(path);
    expect(response.status(), `${path} should not be published`).toBe(404);
  }
});

test("book landing includes cover and points to toc", async ({ page }) => {
  await page.goto("/book/");

  await expect(page.locator('article img[src*="front-page.jpg"]')).toBeVisible();
  await expect(page.locator("article h1")).toContainText(/Threads of Meaning/i);

  const tocLink = page.getByRole("link", { name: /open table of contents/i });
  await expect(tocLink).toBeVisible();
  await expect(tocLink).toHaveAttribute("href", "/book/toc/");
});

test("toc page includes clickable seo-friendly section links", async ({ page }) => {
  await page.goto("/book/toc/");

  const prefaceLink = page.getByRole("link", { name: /^Preface$/ });
  await expect(prefaceLink).toBeVisible();
  await expect(prefaceLink).toHaveAttribute("href", "/book/preface/");

  const tocLinks = page.locator("article ul a");
  const count = await tocLinks.count();
  expect(count).toBeGreaterThan(5);

  const chapterHref = await page
    .locator('article ul a[href*="/book/10-introduction/"]')
    .first()
    .getAttribute("href");
  expect(chapterHref).toBeTruthy();
  expect(chapterHref).toMatch(/^\/book\/[a-z0-9-]+\/[a-z0-9-]+\/$/);

  const textDecoration = await page
    .locator('article ul a[href*="/book/10-introduction/"]')
    .first()
    .evaluate((el) => getComputedStyle(el).textDecorationLine);
  expect(textDecoration).toBe("none");
});

test("section page has previous and next navigation", async ({ page }) => {
  await page.goto("/book/toc/");
  const firstHref = await page.locator("article ul a").first().getAttribute("href");
  expect(firstHref).toBeTruthy();

  await page.goto(firstHref!);
  await expect(page.locator("article h1, article h2").first()).toBeVisible();

  const topPager = page.locator(".book-pager.book-pager-top");
  const bottomPager = page.locator(".book-pager:not(.book-pager-top)");
  await expect(topPager).toBeVisible();
  await expect(bottomPager).toBeVisible();

  await expect(topPager.locator(".prev")).toBeVisible();
  await expect(topPager.locator(".next")).toBeVisible();
  await expect(bottomPager.locator(".prev")).toBeVisible();
  await expect(bottomPager.locator(".next")).toBeVisible();
});

test("section page should not leak markdown or latex control text", async ({ request, page }) => {
  await page.goto("/book/toc/");
  const firstHref = await page.locator("article ul a").first().getAttribute("href");
  expect(firstHref).toBeTruthy();

  const response = await request.get(firstHref!);
  expect(response.status()).toBe(200);

  const html = await response.text();
  expect(html).not.toMatch(/\{\.unnumbered\b/);
  expect(html).not.toMatch(/\b\.unlisted\b/);
  expect(html).not.toContain("\\newpage");
});

test("table of figures page has clickable image links", async ({ page, request }) => {
  await page.goto("/book/table-of-figures/");

  const links = page.locator("article ul a");
  const count = await links.count();
  expect(count).toBeGreaterThan(6);

  const hrefs = await links.evaluateAll((els) => els.map((el) => el.getAttribute("href") || "").filter(Boolean));
  for (const href of hrefs) {
    const response = await request.get(href);
    expect(response.status(), `${href} should be reachable`).toBe(200);
  }
});

test("references page renders bibliography entries", async ({ request }) => {
  const response = await request.get("/book/91-references/references/");
  expect(response.status()).toBe(200);

  const html = await response.text();
  expect(html).toContain('id="refs"');
  expect(html).toContain('class="csl-entry"');
  expect(html).toContain("Alderson-Day");
});

test("core chapter numbering follows Introduction then Chapter 1/2/3", async ({ request }) => {
  const roots = await request.get("/book/11-roots-of-regularity/the-roots-of-regularity/");
  expect(roots.status()).toBe(200);
  const rootsHtml = await roots.text();
  expect(rootsHtml).toContain("Chapter 1: The Roots of Regularity");

  const hierarchy = await request.get("/book/12-hierarchy-of-meaning/a-hierarchy-of-meaning/");
  expect(hierarchy.status()).toBe(200);
  const hierarchyHtml = await hierarchy.text();
  expect(hierarchyHtml).toContain("Chapter 2: A Hierarchy of Meaning");

  const shape = await request.get("/book/13-how-meaning-takes-shape/how-meaning-takes-shape/");
  expect(shape.status()).toBe(200);
  const shapeHtml = await shape.text();
  expect(shapeHtml).toContain("Chapter 3: How Meaning Takes Shape");
});