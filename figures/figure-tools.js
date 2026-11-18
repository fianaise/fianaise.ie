// Download and share buttons under every figure and data table on the site.
//
// Loaded on every page (see _figure-tools.html, included from _quarto.yml).
// For each <iframe> that shows a figure from figures/, it adds:
//   Download data (CSV)  figures/data/<figure>.csv if the build wrote one,
//                        otherwise the numbers read out of the Plotly chart
//   Download image (PNG) the chart as drawn, with a credit line (Plotly charts)
//   Share                the phone's share sheet with the image, or links to
//                        copy, post or email, pointing at this figure on the page
// Tables marked <div class="data-table-wrap" data-figure="<name>"> get the
// CSV and Share buttons, and tables with class "sortable" sort by column.
(function () {
  "use strict";
  const script = document.currentScript;
  const FIGURES = new URL(".", script ? script.src : location.href); // .../figures/
  const CREDIT = "fianaise.ie · CC BY 4.0";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function figureName(src) {
    const m = (src || "").match(/figures\/([^\/?#]+)\.html/);
    return m ? m[1] : null;
  }

  function pageUrl(anchor) {
    return location.origin + location.pathname + (anchor ? "#" + anchor : "");
  }

  function saveBlob(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  // The caption is the paragraph after the figure that starts "**Figure N.**".
  function captionFor(el) {
    let n = el.nextElementSibling;
    while (n && n.classList.contains("figure-tools")) n = n.nextElementSibling;
    if (n && n.tagName === "P" && /^\s*(Figure|Table)\s+\d+/.test(n.textContent)) return n;
    return null;
  }

  function shortTitle(el, fallback) {
    const cap = captionFor(el);
    if (cap) {
      const s = cap.textContent.trim().split(/(?<=\.)\s/).slice(0, 2).join(" ");
      return s.length > 200 ? s.slice(0, 197) + "…" : s;
    }
    return el.getAttribute("title") || fallback || document.title;
  }

  // ── Plotly access ──────────────────────────────────────────────────────────

  async function plotly(frame) {
    if (frame.getAttribute("loading") === "lazy") frame.setAttribute("loading", "eager");
    for (let i = 0; i < 150; i++) {
      let doc;
      try { doc = frame.contentDocument; } catch (e) { return null; }
      const gd = doc && doc.querySelector(".js-plotly-plot");
      const P = frame.contentWindow && frame.contentWindow.Plotly;
      if (gd && P && gd._fullLayout) return { gd, P };
      if (doc && doc.readyState === "complete" && !doc.querySelector(".plotly-graph-div") && i > 20) return null;
      await sleep(100);
    }
    return null;
  }

  const strip = (v) => (typeof v === "string" ? v.replace(/<br\s*\/?>/gi, " ").replace(/<[^>]+>/g, "").trim() : v);

  // Fallback when no CSV was written: one row per point, per visible series.
  function csvFromPlotly(gd) {
    const fields = ["x", "y", "z", "lat", "lon", "locations", "text"];
    const rows = [];
    let maxCustom = 0;
    const traces = gd.data.filter((t) => t.hoverinfo !== "skip" && t.visible !== false);
    traces.forEach((t) => {
      const n = Math.max(0, ...fields.map((f) => (Array.isArray(t[f]) ? t[f].length : 0)));
      for (let i = 0; i < n; i++) {
        const row = { series: strip(t.name || "") };
        fields.forEach((f) => { if (Array.isArray(t[f])) row[f] = strip(t[f][i]); });
        const cd = t.customdata && t.customdata[i];
        if (cd !== undefined) {
          const arr = Array.isArray(cd) ? cd : [cd];
          arr.forEach((v, j) => { row["detail_" + (j + 1)] = strip(v); });
          maxCustom = Math.max(maxCustom, arr.length);
        }
        rows.push(row);
      }
    });
    const cols = ["series", ...fields.filter((f) => rows.some((r) => r[f] !== undefined))];
    for (let j = 1; j <= maxCustom; j++) cols.push("detail_" + j);
    const esc = (v) => {
      if (v === undefined || v === null) return "";
      const s = String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const lines = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))];
    lines.push("", esc("Source: " + pageUrl()));
    return new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  }

  async function csvBlob(name, frame) {
    try {
      const r = await fetch(new URL("data/" + name + ".csv", FIGURES));
      if (r.ok) return await r.blob();
    } catch (e) { /* fall through */ }
    if (frame) {
      const p = await plotly(frame);
      if (p) return csvFromPlotly(p.gd);
    }
    throw new Error("no data");
  }

  // The chart as a PNG at twice its on-screen size, with a credit strip below.
  async function pngBlob(frame) {
    const p = await plotly(frame);
    if (!p) throw new Error("not a chart");
    const { gd, P } = p;
    const w = gd.offsetWidth || 800;
    const h = gd.offsetHeight || 500;
    // Tiled maps can stall if a tile won't load; give up after 20 seconds.
    const url = await Promise.race([
      P.toImage(gd, { format: "png", width: w, height: h, scale: 2 }),
      sleep(20000).then(() => { throw new Error("timed out"); }),
    ]);
    const img = new Image();
    await new Promise((ok, bad) => { img.onload = ok; img.onerror = bad; img.src = url; });
    const pad = 44 * 2;
    const c = document.createElement("canvas");
    c.width = img.width;
    c.height = img.height + pad;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0);
    ctx.fillStyle = "#e8e7e3";
    ctx.fillRect(0, img.height, c.width, 2);
    ctx.font = "26px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#52514e";
    ctx.fillText(CREDIT, 28, img.height + pad / 2);
    ctx.textAlign = "right";
    ctx.fillStyle = "#8a8984";
    ctx.fillText(location.host + location.pathname.replace(/\.html$/, ""), c.width - 28, img.height + pad / 2);
    return await new Promise((ok) => c.toBlob(ok, "image/png"));
  }

  // ── Buttons ────────────────────────────────────────────────────────────────

  function button(label, title) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn btn-sm btn-outline-dark";
    b.textContent = label;
    if (title) b.title = title;
    return b;
  }

  function toolbar(el, name, anchor, frame) {
    const bar = document.createElement("div");
    bar.className = "figure-tools";
    const status = document.createElement("span");
    status.className = "figure-tools-status";
    status.setAttribute("role", "status");
    const say = (t) => { status.textContent = t; clearTimeout(say.t); say.t = setTimeout(() => { status.textContent = ""; }, 5000); };
    const busy = async (b, work) => {
      b.disabled = true;
      try { await work(); } finally { b.disabled = false; }
    };

    const csv = button("Download data (CSV)", "The numbers behind this figure, as a spreadsheet file");
    csv.addEventListener("click", () => busy(csv, async () => {
      try { saveBlob(await csvBlob(name, frame), name + ".csv"); }
      catch (e) { say("Sorry, the data for this figure isn't available to download."); }
    }));
    bar.appendChild(csv);

    let png = null;
    let pngPromise = null;
    const image = () => (pngPromise = pngPromise || pngBlob(frame).catch((e) => { pngPromise = null; throw e; }));
    if (frame) {
      png = button("Download image (PNG)", "This chart as a picture, with a credit line");
      png.addEventListener("click", () => busy(png, async () => {
        say("Making the image…");
        try { saveBlob(await image(), name + ".png"); say(""); }
        catch (e) { say("Sorry, this figure can't be saved as an image. Try a screenshot."); }
      }));
      bar.appendChild(png);
      // Charts that aren't Plotly (the charities graphic) have no PNG export.
      frame.addEventListener("load", async () => {
        try {
          const doc = frame.contentDocument;
          if (doc && !doc.querySelector(".plotly-graph-div")) png.hidden = true;
        } catch (e) { png.hidden = true; }
      });
    }

    const share = button("Share", "Share this figure");
    share.setAttribute("aria-expanded", "false");
    const menu = document.createElement("div");
    menu.className = "figure-share-menu";
    menu.hidden = true;
    const link = pageUrl(anchor);
    const text = shortTitle(el, name);
    const enc = encodeURIComponent;
    const items = [];
    if (frame && navigator.canShare) {
      items.push(["Share image…", async () => {
        try {
          const file = new File([await image()], name + ".png", { type: "image/png" });
          if (navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], title: document.title, text: text + " " + link });
          } else {
            await navigator.share({ title: document.title, text: text, url: link });
          }
        } catch (e) { if (e.name !== "AbortError") say("Sharing didn't work here. Try Copy link."); }
      }]);
    } else if (navigator.share) {
      items.push(["Share…", async () => {
        try { await navigator.share({ title: document.title, text: text, url: link }); }
        catch (e) { if (e.name !== "AbortError") say("Sharing didn't work here. Try Copy link."); }
      }]);
    }
    items.push(["Copy link", async () => {
      try { await navigator.clipboard.writeText(link); say("Link copied."); }
      catch (e) { say(link); }
    }]);
    if (frame && window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
      items.push(["Copy image", async () => {
        try {
          await navigator.clipboard.write([new ClipboardItem({ "image/png": image() })]);
          say("Image copied. Paste it into a post or document.");
        } catch (e) { say("Couldn't copy the image here. Use Download image instead."); }
      }]);
    }
    const links = [
      ["Bluesky", "https://bsky.app/intent/compose?text=" + enc(text + " " + link)],
      ["X", "https://x.com/intent/post?text=" + enc(text) + "&url=" + enc(link)],
      ["LinkedIn", "https://www.linkedin.com/sharing/share-offsite/?url=" + enc(link)],
      ["Facebook", "https://www.facebook.com/sharer/sharer.php?u=" + enc(link)],
      ["WhatsApp", "https://wa.me/?text=" + enc(text + " " + link)],
      ["Email", "mailto:?subject=" + enc(document.title) + "&body=" + enc(text + "\n\n" + link)],
    ];
    items.forEach(([label, act]) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.addEventListener("click", async () => { await act(); close(); });
      menu.appendChild(b);
    });
    links.forEach(([label, href]) => {
      const a = document.createElement("a");
      a.href = href;
      a.textContent = label;
      if (!href.startsWith("mailto:")) { a.target = "_blank"; a.rel = "noopener"; }
      a.addEventListener("click", () => close());
      menu.appendChild(a);
    });
    const close = () => { menu.hidden = true; share.setAttribute("aria-expanded", "false"); };
    share.addEventListener("click", () => {
      const open = menu.hidden;
      menu.hidden = !open;
      share.setAttribute("aria-expanded", String(open));
      if (open && frame) image().catch(() => {}); // get the image ready for Share/Copy image
    });
    document.addEventListener("click", (e) => { if (!bar.contains(e.target)) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });

    const wrap = document.createElement("span");
    wrap.className = "figure-share";
    wrap.append(share, menu);
    bar.append(wrap, status);
    return bar;
  }

  // ── Fit charts to the screen ───────────────────────────────────────────────
  // The charts are drawn for a laptop. On a narrower screen (an iPad, a phone)
  // this wraps titles that would be cut off, shrinks labels and legends that
  // don't fit, puts side-by-side maps one above the other, and makes the frame
  // taller to suit. At laptop width it leaves the chart as drawn.
  const STACK_BELOW = 640; // px of frame width
  const measureCtx = document.createElement("canvas").getContext("2d");
  function textWidth(t, size, bold, family) {
    measureCtx.font = (bold ? "700 " : "400 ") + size + "px " + family;
    return measureCtx.measureText(t).width;
  }

  // Re-wrap Plotly's pseudo-HTML so no line is wider than `max` pixels.
  function wrapText(text, max, base, family) {
    if (typeof text !== "string" || !text) return text;
    const tokens = text.match(/<[^>]+>|[^\s<]+|\s+/g) || [];
    const stack = [{ bold: false, size: base }];
    let out = "", lineW = 0, space = false;
    for (const t of tokens) {
      const cur = stack[stack.length - 1];
      if (t[0] === "<") {
        if (/^<br/i.test(t)) { out += t; lineW = 0; space = false; }
        else if (t[1] === "/") { if (stack.length > 1) stack.pop(); out += t; }
        else {
          const m = t.match(/font-size:\s*(\d+)/i);
          stack.push({ bold: cur.bold || /^<b\b/i.test(t), size: m ? +m[1] : cur.size });
          out += t;
        }
        continue;
      }
      if (/^\s+$/.test(t)) { space = true; continue; }
      const w = textWidth(t, cur.size, cur.bold, family);
      const sw = space ? textWidth(" ", cur.size, cur.bold, family) : 0;
      if (lineW > 0 && lineW + sw + w > max) { out += "<br>"; lineW = w; }
      else { out += space ? " " : ""; lineW += sw + w; }
      out += t;
      space = false;
    }
    return out;
  }

  function widestLine(text, size, family) {
    return Math.max(0, ...String(text).split(/<br\s*\/?>/i).map((l) =>
      textWidth(l.replace(/<[^>]+>/g, ""), size, /<b\b/i.test(l), family)));
  }

  function fitChart(frame) {
    let orig = null, lastW = 0, running = false, again = false;

    async function run() {
      if (running) { again = true; return; }
      running = true;
      try { await apply(); } catch (e) { /* leave the chart as drawn */ }
      running = false;
      if (again) { again = false; run(); }
    }

    async function apply() {
      let doc, P, gd;
      for (let i = 0; i < 50; i++) {
        try { doc = frame.contentDocument; } catch (e) { return; }
        gd = doc && doc.querySelector(".js-plotly-plot");
        P = frame.contentWindow && frame.contentWindow.Plotly;
        if (gd && P && gd._fullLayout) break;
        await sleep(100);
      }
      if (!gd || !P || !gd._fullLayout) return;
      // Tiled maps redraw their own way; leave them as drawn.
      const sp = gd._fullLayout._subplots || {};
      if ((sp.mapbox && sp.mapbox.length) || (sp.map && sp.map.length)) return;
      const W = frame.clientWidth;
      if (!W || Math.abs(W - lastW) < 2) return;
      lastW = W;
      if (!orig) {
        orig = {
          layout: JSON.parse(JSON.stringify(gd.layout)),
          names: (gd.data || []).map((t) => t.name),
          frameH: frame.offsetHeight,
        };
      }
      const L = orig.layout;
      const fl = gd._fullLayout;
      const family = (fl.font && fl.font.family) || "sans-serif";
      const m = Object.assign({ l: 80, r: 80, t: 100, b: 80 }, L.margin || {});
      const sz = fl._size || {};
      const plotW = sz.w || (W - m.l - m.r);
      const padL = sz.l != null ? sz.l : m.l, padR = sz.r != null ? sz.r : m.r;
      const u = {};

      // Two maps side by side → one above the other.
      const g1 = L.geo && L.geo.domain, g2 = L.geo2 && L.geo2.domain;
      const sideBySide = g1 && g2 && g1.x && g2.x && g1.x[1] <= 0.51 && g2.x[0] >= 0.49 && !L.geo3;
      const stack = sideBySide && W < STACK_BELOW;
      let plotH = null, gap = 0, topGap = 0;
      if (sideBySide) {
        if (stack) {
          const mapH = Math.round(plotW * 1.15);
          const gapPx = 84, topPx = 56;
          plotH = 2 * mapH + gapPx + topPx;
          gap = gapPx / plotH;
          topGap = topPx / plotH;
          u["geo.domain"] = { x: [0, 1], y: [0.5 + gap / 2, 1 - topGap] };
          u["geo2.domain"] = { x: [0, 1], y: [0, 0.5 - gap / 2] };
        } else {
          u["geo.domain"] = g1;
          u["geo2.domain"] = g2;
        }
      }

      // Title: wrap to the frame; say top/bottom rather than left/right.
      if (L.title && L.title.text) {
        let t = L.title.text;
        if (stack) t = t.replace(/\bLeft:/g, "Top:").replace(/\bRight:/g, "Bottom:").replace(/\bleft\b/g, "top").replace(/\bright\b/g, "bottom");
        const size = (L.title.font && L.title.font.size) || (fl.title && fl.title.font && fl.title.font.size) || 17;
        u["title.text"] = wrapText(t, W * 0.96 - 18, size, family);
      }

      // Annotations: subplot titles wrap; other labels shrink to fit.
      (L.annotations || []).forEach((a, i) => {
        if (!a || typeof a.text !== "string") return;
        const size = (a.font && a.font.size) || 12;
        const mid = (d) => d && d.x ? (d.x[0] + d.x[1]) / 2 : null;
        const which = sideBySide && a.xref !== "x" && Math.abs(a.x - mid(g1)) < 0.02 ? 1
          : sideBySide && a.xref !== "x" && Math.abs(a.x - mid(g2)) < 0.02 ? 2 : 0;
        if (which) {
          const p = "annotations[" + i + "].";
          if (stack) {
            u[p + "x"] = 0.5;
            u[p + "y"] = which === 1 ? 1 - topGap : 0.5 - gap / 2 + 0.004;
            u[p + "yanchor"] = "bottom";
            u[p + "text"] = wrapText(a.text, plotW - 8, size, family);
          } else {
            u[p + "x"] = a.x; u[p + "y"] = a.y;
            u[p + "yanchor"] = a.yanchor || "auto";
            u[p + "text"] = wrapText(a.text, (plotW / 2) - 8, size, family);
          }
          return;
        }
        // Where the label sits across the plot, from 0 (left) to 1 (right).
        let x = typeof a.x === "number" ? a.x : 0.5;
        if (a.xref && a.xref !== "paper") {
          const ax = fl[a.xref.replace(/^x/, "xaxis")];
          if (!ax || !ax.range || ax.type === "category") return;
          const [r0, r1] = ax.range.map(Number), d = ax.domain || [0, 1];
          x = d[0] + (x - r0) / (r1 - r0) * (d[1] - d[0]);
        }
        const anchor = a.xanchor || "auto";
        if (anchor === "center" || (anchor === "auto" && Math.abs(x - 0.5) < 0.02)) {
          u["annotations[" + i + "].text"] = wrapText(a.text, plotW - 8, size, family);
          return;
        }
        const room = anchor === "right" ? x * plotW + padL - 6 : (1 - x) * plotW + padR - 6;
        const need = widestLine(a.text, size, family) * 1.08;
        if (room > 40 && need > room) u["annotations[" + i + "].font.size"] = Math.max(10, Math.floor(size * room / need));
        else if (a.font && a.font.size) u["annotations[" + i + "].font.size"] = size;
      });

      // Legends: smaller text on a phone, and long entries wrapped.
      const narrow = W < STACK_BELOW;
      const names = { name: [] }, nameIdx = [];
      if (L.showlegend !== false && fl.showlegend) {
        const size = (L.legend && L.legend.font && L.legend.font.size) || 12;
        const lsize = narrow ? Math.min(size, 12) : size;
        u["legend.font.size"] = lsize;
        (gd.data || []).forEach((t, i) => {
          const was = orig.names[i];
          if (typeof was !== "string" || t.showlegend === false) return;
          const now = narrow ? wrapText(was, W - 80, lsize, family) : was;
          if (now !== t.name) { names.name.push(now); nameIdx.push(i); }
        });
      }

      // Axis labels: a size smaller on a phone so long category names fit.
      Object.keys(L).filter((k) => /^[xy]axis\d*$/.test(k)).forEach((k) => {
        const size = (L[k].tickfont && L[k].tickfont.size) || null;
        if (size && size > 11) u[k + ".tickfont.size"] = narrow ? 11 : size;
      });

      let baseH = plotH ? plotH + m.t + m.b : (L.height || orig.frameH);
      // A single map on a phone needs less height than on a laptop.
      const geos = (gd._fullLayout._subplots || {}).geo || [];
      if (!plotH && geos.length === 1 && W < STACK_BELOW) baseH = Math.min(baseH, m.t + m.b + Math.round(plotW * 1.3));
      u["margin.t"] = m.t;
      u["margin.b"] = m.b;
      if (L.legend) {
        const lg = L.legend;
        Object.assign(u, { "legend.x": lg.x, "legend.xanchor": lg.xanchor, "legend.y": lg.y,
          "legend.yanchor": lg.yanchor, "legend.yref": lg.yref || "paper" });
      }
      u.height = baseH;
      if (nameIdx.length) await P.restyle(gd, names, nameIdx);
      await P.relayout(gd, u);

      // If the legend now runs into a label (as the map titles do once the
      // legend wraps), move the legend under the chart.
      const leg = gd.querySelector(".legend");
      let legExtra = 0;
      if (leg) {
        const lr = leg.getBoundingClientRect();
        const hit = Array.from(gd.querySelectorAll(".annotation")).some((el) => {
          const r = el.getBoundingClientRect();
          return r.height && r.left < lr.right && r.right > lr.left && r.top < lr.bottom && r.bottom > lr.top;
        });
        if (hit) {
          legExtra = Math.ceil(lr.height) + 12;
          await P.relayout(gd, { "legend.y": 0, "legend.yanchor": "top", "legend.yref": "container",
            "legend.x": 0.02, "legend.xanchor": "left", "margin.b": m.b + legExtra, height: baseH + legExtra });
          await P.relayout(gd, { "legend.y": (legExtra - 4) / (baseH + legExtra) });
        }
      }
      baseH += legExtra;

      // Make room if the wrapped title now runs into the legend or labels.
      const top = gd.getBoundingClientRect().top;
      const title = gd.querySelector(".g-gtitle");
      const titleBottom = title ? title.getBoundingClientRect().bottom - top : 0;
      let highest = Infinity;
      gd.querySelectorAll(".legend, .annotation, .updatemenu-header-group").forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.height && r.top - top < m.t) highest = Math.min(highest, r.top - top);
      });
      if (highest === Infinity) highest = m.t;
      const extra = Math.max(0, Math.ceil(titleBottom + 8 - highest));
      if (extra) await P.relayout(gd, { "margin.t": m.t + extra, height: baseH + extra });
      frame.style.height = (baseH + extra) + "px";
    }

    frame.addEventListener("load", () => { lastW = 0; run(); });
    run();
    return run;
  }

  const fitRuns = [];
  document.querySelectorAll('iframe[src*="figures/"]').forEach((frame) => fitRuns.push(fitChart(frame)));
  let fitTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(fitTimer);
    fitTimer = setTimeout(() => fitRuns.forEach((r) => r()), 200);
  });

  // ── Wide tables scroll sideways on a phone rather than widening the page ───
  document.querySelectorAll("main table").forEach((table) => {
    const parent = table.parentElement;
    if (!parent || parent.closest(".data-table-wrap, .table-scroll, .table-responsive")) return;
    const wrap = document.createElement("div");
    wrap.className = "table-scroll";
    parent.insertBefore(wrap, table);
    wrap.append(table);
  });

  // ── Collapsible captions ───────────────────────────────────────────────────
  // Each caption is a short title, then a ".caption-details" block with the
  // full description and sources. Fold that block behind a button so long
  // captions don't fill a phone screen. Without this script it simply shows.
  document.querySelectorAll("div.caption-details").forEach((div) => {
    const details = document.createElement("details");
    details.className = "caption-details";
    const summary = document.createElement("summary");
    summary.innerHTML = '<span class="when-closed">Show details and sources</span><span class="when-open">Hide details and sources</span>';
    details.append(summary);
    while (div.firstChild) details.append(div.firstChild);
    div.replaceWith(details);
  });
  // Open the details when someone follows a link to something inside them.
  const openTarget = () => {
    const el = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const d = el && el.closest("details.caption-details");
    if (d) d.open = true;
  };
  openTarget();
  window.addEventListener("hashchange", openTarget);

  // ── Wire up figures and tables ─────────────────────────────────────────────

  document.querySelectorAll('iframe[src*="figures/"]').forEach((frame) => {
    const name = figureName(frame.getAttribute("src"));
    if (!name) return;
    if (!frame.id) frame.id = "fig-" + name.replace(/_/g, "-");
    frame.after(toolbar(frame, name, frame.id, frame));
  });

  document.querySelectorAll(".data-table-wrap[data-figure]").forEach((wrap) => {
    const name = wrap.getAttribute("data-figure");
    if (!wrap.id) wrap.id = "table-" + name.replace(/_/g, "-");
    wrap.after(toolbar(wrap, name, wrap.id, null));
  });

  // Sortable tables: click a column heading to sort; click again to reverse.
  document.querySelectorAll("table.sortable").forEach((table) => {
    const body = table.tBodies[0];
    const headRows = table.tHead ? table.tHead.rows : [];
    const heads = headRows.length ? Array.from(headRows[headRows.length - 1].cells) : [];
    const value = (row, i) => {
      const cell = row.cells[i];
      const v = cell.getAttribute("data-value");
      if (v !== null) return parseFloat(v);
      const n = parseFloat(cell.textContent.replace(/[,%]/g, ""));
      return isNaN(n) ? cell.textContent.trim().toLowerCase() : n;
    };
    heads.forEach((th, i) => {
      th.tabIndex = 0;
      th.setAttribute("aria-sort", "none");
      const sort = () => {
        const asc = th.getAttribute("aria-sort") !== "ascending" && (i === 0 || th.getAttribute("aria-sort") === "descending");
        heads.forEach((h) => h.setAttribute("aria-sort", "none"));
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        const rows = Array.from(body.rows);
        rows.sort((a, b) => {
          const x = value(a, i), y = value(b, i);
          const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
          return asc ? c : -c;
        });
        rows.forEach((r) => body.appendChild(r));
      };
      th.addEventListener("click", sort);
      th.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } });
    });
  });

  // A link to a figure (#fig-...) scrolls to it once the page has laid out.
  if (location.hash && /^#(fig|table)-/.test(location.hash)) {
    const el = document.getElementById(location.hash.slice(1));
    if (el) setTimeout(() => el.scrollIntoView({ block: "start" }), 300);
  }
})();
