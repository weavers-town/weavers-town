import { test } from "@playwright/test";
import path from "node:path";

const pagesToScreenshot = [
  { path: "/", name: "homepage" },
  { path: "/book/", name: "book-landing" },
  { path: "/book/toc/", name: "book-toc" },
  { path: "/explorations/", name: "explorations" },
  { path: "/book/11-roots-of-regularity/the-roots-of-regularity/", name: "sample-chapter" },
];

test.describe("Visual inspection of redesign", () => {
  for (const pageInfo of pagesToScreenshot) {
    test(`screenshot - ${pageInfo.name}`, async ({ page }, testInfo) => {
      await page.goto(pageInfo.path, { waitUntil: "networkidle" });

      // Give animations / fonts a moment
      await page.waitForTimeout(800);

      const screenshotPath = testInfo.outputDir + `/${pageInfo.name}.png`;

      await page.screenshot({
        path: screenshotPath,
        fullPage: true,
      });

      console.log(`Saved screenshot: ${screenshotPath}`);
    });
  }
});