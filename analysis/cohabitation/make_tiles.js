// Draws the project tiles for "Cohabitation in Ireland" (images/cohabitation*.png) with Playwright.
// Run from the repository root: node analysis/cohabitation/make_tiles.js
const { chromium } = require("playwright");
const path = require("path");

// [file, heading, line under it, colour of the heading]
const tiles = [
  ["cohabitation-cost.png", "The cost of not marrying", "", "#c4501f"],
  ["cohabitation-calculator.png", "Calculator", "", "#2a78d6"],
  ["cohabitation-constitution.png", "The Constitution and the courts", "", "#158a60"],
];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  for (const [file, big, small, colour] of tiles) {
    await page.setContent(`<!doctype html><html><body style="margin:0;width:1200px;height:800px;background:#f3f2ee;
      font-family:'Source Sans Pro','Liberation Sans',Arial,sans-serif;display:flex;flex-direction:column;justify-content:center;padding:0 110px;box-sizing:border-box">
      <div style="font-size:${big.length > 14 ? 150 : 170}px;font-weight:700;color:${colour};line-height:1.05;letter-spacing:-2px">${big}</div>
      ${small ? `<div style="margin-top:44px;font-size:52px;line-height:1.25;color:#2b2a28;max-width:960px">${small}</div>` : ""}
      </body></html>`);
    await page.screenshot({ path: path.join(__dirname, "..", "..", "images", file) });
  }
  // Home page cover: inheritance tax on a €300,000 half share of a home, married and not.
  await page.setContent(`<!doctype html><html><body style="margin:0;width:1200px;height:800px;background:#f3f2ee;
    font-family:'Source Sans Pro','Liberation Sans',Arial,sans-serif;box-sizing:border-box;padding:90px 110px;display:flex;flex-direction:column;justify-content:center">
    <div style="font-size:44px;color:#2b2a28;margin-bottom:50px">Inheritance tax on a €300,000 half share of a home</div>
    <div style="display:grid;grid-template-columns:260px 1fr;row-gap:40px;align-items:center;font-size:44px;color:#2b2a28">
      <div>Married</div><div style="display:flex;align-items:center;gap:24px"><div style="width:6px;height:110px;background:#52514e"></div><b style="font-size:64px">€0</b></div>
      <div>Not married</div><div style="display:flex;align-items:center;gap:24px"><div style="width:500px;height:110px;background:#c4501f;border-radius:0 6px 6px 0"></div><b style="font-size:64px;color:#c4501f">€91,740</b></div>
    </div></body></html>`);
  await page.screenshot({ path: path.join(__dirname, "..", "..", "images", "cohabitation.png") });
  await browser.close();
})();
