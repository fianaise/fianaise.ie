// Writes the worked-examples table on cohabitation/cost.qmd from the rules in cohabitation/tax-rules.js.
// Run from the repository root: node analysis/cohabitation/make_examples.js
const fs = require("fs");
const path = require("path");
const t = require(path.join(__dirname, "..", "..", "cohabitation", "tax-rules.js"));

const eur = (x) => "€" + Math.round(x).toLocaleString("en-IE");
const examples = [
  ["One earner on €60,000, partner at home", 60000, 0],
  ["One earner on €100,000, partner at home", 100000, 0],
  ["One earner on €40,000, partner at home", 40000, 0],
  ["€70,000 and €20,000", 70000, 20000],
  ["€90,000 and €30,000", 90000, 30000],
  ["Two earners on €50,000 each", 50000, 50000],
];

let out = "| Household | Income tax if married | Income tax if not married | Extra each year |\n|---|--:|--:|--:|\n";
for (const [label, a, b] of examples) {
  out += `| ${label} | ${eur(t.incomeTaxMarried(a, b))} | ${eur(t.incomeTaxSeparate(a, b))} | **${eur(t.incomeTaxGap(a, b))}** |\n`;
}
fs.writeFileSync(path.join(__dirname, "..", "..", "cohabitation", "_income-tax-examples.md"), out);
process.stdout.write(out);
