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
  // Home page cover: one couple in six is cohabiting (CSO Census 2022, table F3035).
  const pair = (on) => `<div style="display:flex;gap:10px"><div style="width:48px;height:48px;border-radius:50%;background:${on ? "#c4501f" : "#c9c7c0"}"></div><div style="width:48px;height:48px;border-radius:50%;background:${on ? "#c4501f" : "#c9c7c0"}"></div></div>`;
  await page.setContent(`<!doctype html><html><body style="margin:0;width:1200px;height:800px;background:#f3f2ee;
    font-family:'Source Sans Pro','Liberation Sans',Arial,sans-serif;box-sizing:border-box;padding:80px 110px;display:flex;flex-direction:column;justify-content:center">
    <div style="display:flex;gap:40px;margin-bottom:60px">${[1, 0, 0, 0, 0, 0].map(pair).join("")}</div>
    <div style="font-size:120px;font-weight:700;color:#c4501f;line-height:1">1 in 6</div>
    <div style="font-size:48px;color:#2b2a28;margin-top:24px">couples in Ireland live together without marrying</div></body></html>`);
  await page.screenshot({ path: path.join(__dirname, "..", "..", "images", "cohabitation.png") });
  await browser.close();
})();
