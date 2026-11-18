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
