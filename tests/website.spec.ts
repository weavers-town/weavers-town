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

test("farsi home page renders key content", async ({ page }) => {
  await page.goto("/fa/");

  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page).toHaveTitle(/نخ/i);
  await expect(page.locator("h1", { hasText: "نخ" })).toBeVisible();
  await expect(page.getByRole("link", { name: /خواندن کتاب/i }).first()).toBeVisible();
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

  await page.getByRole("button", { name: "Language" }).click();
  await page.getByRole("menuitem", { name: "فارسی" }).click();
  await expect(page).toHaveURL(/\/fa\/book\//);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
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
    .locator('article ul a[href*="/book/11-introduction/"]')
    .first()
    .getAttribute("href");
  expect(chapterHref).toBeTruthy();
  expect(chapterHref).toMatch(/^\/book\/[a-z0-9-]+\/[a-z0-9-]+\/$/);

  const textDecoration = await page
    .locator('article ul a[href*="/book/11-introduction/"]')
    .first()
    .evaluate((el) => getComputedStyle(el).textDecorationLine);
  expect(textDecoration).toBe("none");

  // Reading order: grounding chapter before Introduction; copyright once.
  const tocHrefs = await page.locator("article ul a").evaluateAll((links) =>
    links.map((el) => el.getAttribute("href") || ""),
  );
  const groundingIdx = tocHrefs.findIndex((h) => h.includes("/book/10-what-we-actually-mean-by-meaning/"));
  const introIdx = tocHrefs.findIndex((h) => h.includes("/book/11-introduction/"));
  const rootsIdx = tocHrefs.findIndex((h) => h.includes("/book/12-roots-of-regularity/"));
  expect(groundingIdx).toBeGreaterThanOrEqual(0);
  expect(introIdx).toBeGreaterThan(groundingIdx);
  expect(rootsIdx).toBeGreaterThan(introIdx);

  const copyrightLinks = page.locator('article ul a[href="/book/copyright/"]');
  await expect(copyrightLinks).toHaveCount(1);
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

test("core chapter numbering: grounding, Introduction, then Chapters 1–3", async ({ request }) => {
  const meaning = await request.get("/book/10-what-we-actually-mean-by-meaning/what-we-actually-mean-by-meaning/");
  expect(meaning.status()).toBe(200);
  const meaningHtml = await meaning.text();
  expect(meaningHtml).toContain("What We Actually Mean by Meaning");
  expect(meaningHtml).not.toContain("Chapter 1: What We Actually Mean by Meaning");

  const intro = await request.get("/book/11-introduction/introduction-the-threads-of-meaning/");
  expect(intro.status()).toBe(200);
  const introHtml = await intro.text();
  expect(introHtml).toContain("Introduction: The Threads of Meaning");
  expect(introHtml).toContain("previous chapter");

  const roots = await request.get("/book/12-roots-of-regularity/the-roots-of-regularity/");
  expect(roots.status()).toBe(200);
  const rootsHtml = await roots.text();
  expect(rootsHtml).toContain("Chapter 1: The Roots of Regularity");

  const hierarchy = await request.get("/book/13-hierarchy-of-meaning/a-hierarchy-of-meaning/");
  expect(hierarchy.status()).toBe(200);
  const hierarchyHtml = await hierarchy.text();
  expect(hierarchyHtml).toContain("Chapter 2: A Hierarchy of Meaning");

  const weavers = await request.get("/book/15-the-weavers-way-a-meta-ideology-in-practice/the-weaver-s-way-a-meta-ideology-in-practice/");
  expect(weavers.status()).toBe(200);
  const weaversHtml = await weavers.text();
  expect(weaversHtml).toContain("Chapter 4: The Weaver");
});