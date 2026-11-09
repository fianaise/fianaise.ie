// Irish tax rules used by the "Marriage in Ireland" calculator and worked examples.
// Tax year 2027 (Budget 2027, announced 6 October 2026). Update this file after each Budget.
// Sources are listed on marriage/sources.qmd; each value notes where it comes from.
(function (root) {
  "use strict";

  var RULES = {
    year: 2027,
    // Citizens Information, Budget 2027: rates "remain the same at 20% and 40%".
    standardRate: 0.20,
    higherRate: 0.40,
    // Standard rate band. Single: EUR 46,500 (Citizens Information, Budget 2027).
    // Married, one income: EUR 55,500; two incomes: increased by the lower of EUR 37,500
    // or the lower earner's income (KPMG, Budget 2027 headlines).
    bandSingle: 46500,
    bandMarried: 55500,
    bandMarriedIncreaseMax: 37500,
    // Personal tax credit EUR 2,125 per person (Citizens Information, Budget 2027).
    // A married couple or civil partners get a personal credit for each spouse.
    personalCredit: 2125,
    // Employee (PAYE) tax credit EUR 2,125, limited to 20% of the earner's PAYE income.
    employeeCredit: 2125,
    // Capital Acquisitions Tax: 33%; Group C threshold EUR 22,000 from 7 October 2026 (Revenue).
    // Spouses and civil partners are exempt (Revenue).
    catRate: 0.33,
    catGroupC: 22000,
    // Capital Gains Tax: 31% for disposals on or after 7 October 2026; EUR 1,270 annual
    // exemption per person; transfers between spouses are exempt (Citizens Information).
    cgtRate: 0.31,
    cgtExemption: 1270
  };

  function taxOnIncome(income, band, rules) {
    var lower = Math.min(income, band);
    var upper = Math.max(0, income - band);
    return lower * rules.standardRate + upper * rules.higherRate;
  }

  function employeeCredit(income, rules) {
    return Math.min(rules.employeeCredit, income * rules.standardRate);
  }

  // Two people taxed as single, unconnected individuals (cohabiting couples).
  // Credits are not refundable, so each person's tax floors at zero.
  function incomeTaxSeparate(a, b, rules) {
    rules = rules || RULES;
    function one(x) {
      var gross = taxOnIncome(x, rules.bandSingle, rules);
      return Math.max(0, gross - rules.personalCredit - employeeCredit(x, rules));
    }
    return one(a) + one(b);
  }

  // A married couple under joint assessment. A married couple can instead choose separate
  // treatment, so they pay the lower of the two.
  function incomeTaxMarried(a, b, rules) {
    rules = rules || RULES;
    var low = Math.min(a, b);
    var band = rules.bandMarried + Math.min(rules.bandMarriedIncreaseMax, low);
    var gross = taxOnIncome(a + b, band, rules);
    var credits = 2 * rules.personalCredit + employeeCredit(a, rules) + employeeCredit(b, rules);
    var joint = Math.max(0, gross - credits);
    return Math.min(joint, incomeTaxSeparate(a, b, rules));
  }

  function incomeTaxGap(a, b, rules) {
    return incomeTaxSeparate(a, b, rules) - incomeTaxMarried(a, b, rules);
  }

  // Inheritance from a partner: a spouse pays nothing; a cohabitant is a "stranger in blood"
  // (Group C). Assumes no earlier Group C gifts or inheritances, and no reliefs.
  function inheritanceTaxCohabitant(value, rules) {
    rules = rules || RULES;
    return Math.max(0, value - rules.catGroupC) * rules.catRate;
  }

  // CGT on a gain when one partner transfers an asset to the other during life.
  function cgtCohabitant(gain, rules) {
    rules = rules || RULES;
    return Math.max(0, gain - rules.cgtExemption) * rules.cgtRate;
  }

  var api = {
    RULES: RULES,
    incomeTaxSeparate: incomeTaxSeparate,
    incomeTaxMarried: incomeTaxMarried,
    incomeTaxGap: incomeTaxGap,
    inheritanceTaxCohabitant: inheritanceTaxCohabitant,
    cgtCohabitant: cgtCohabitant
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MarriageTax = api;
})(this);
