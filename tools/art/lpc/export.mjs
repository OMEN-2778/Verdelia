// Exports our characters from the Universal LPC generator (fetched by fetch.py): starts its dev
// server, opens each character of characters.json from its hash in a headless browser and saves
// the generator's "ZIP: Split by animation and item" (every layer of every animation as its own
// sheet, already coloured) and "Credits (CSV)" into .cache/export/<id>/, unzipped into x/.
//
//   node tools/art/lpc/export.mjs [ids...]
//
// A Chromium is needed: Playwright's own, or the one named by $CHROMIUM.
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const ulpc = path.join(here, ".cache", "ulpc");
const port = 5199;
const { chromium } = await import(pathToFileURL(path.join(ulpc, "node_modules/playwright-core/index.mjs")).href);

const specs = JSON.parse(fs.readFileSync(path.join(here, "characters.json"), "utf8"));
const ids = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(specs);

const server = spawn(path.join(ulpc, "node_modules/.bin/vite"), ["--port", String(port), "--strictPort"], {
  cwd: ulpc,
  stdio: "ignore",
});
try {
  await waitForServer();
  const exe = process.env.CHROMIUM || (fs.existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined);
  const browser = await chromium.launch({ executablePath: exe });
  for (const id of ids) {
    await exportOne(browser, id, specs[id].hash);
  }
  await browser.close();
} finally {
  server.kill();
}

async function waitForServer() {
  for (let i = 0; i < 120; i++) {
    try {
      const r = await fetch(`http://localhost:${port}/`);
      if (r.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("the generator's dev server did not start");
}

async function exportOne(browser, id, hash) {
  const out = path.join(here, ".cache", "export", id);
  fs.rmSync(out, { recursive: true, force: true });
  fs.mkdirSync(out, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 }, acceptDownloads: true });
  await page.goto(`http://localhost:${port}/#${hash}`, { waitUntil: "networkidle", timeout: 120000 });
  await page.evaluate(() => window.__LPC_waitCatalogAllReady && window.__LPC_waitCatalogAllReady());
  await page.waitForTimeout(2500);
  // the generator drops what it does not know (a misspelt item, a colour it lacks): say so
  const got = new Set(decodeURIComponent(await page.evaluate(() => location.hash)).slice(1).split("&"));
  const lost = hash.split("&").filter((p) => !got.has(p));
  if (lost.length) console.warn(`${id}: the generator dropped ${lost.join(", ")}`);
  fs.writeFileSync(path.join(out, "hash.txt"), [...got].join("&") + "\n");
  for (const [label, file] of [
    ["ZIP: Split by animation and item", "items.zip"],
    ["Credits (CSV)", "credits.csv"],
  ]) {
    const [dl] = await Promise.all([
      page.waitForEvent("download", { timeout: 120000 }),
      page.getByText(label, { exact: true }).first().click(),
    ]);
    await dl.saveAs(path.join(out, file));
  }
  await page.close();
  fs.mkdirSync(path.join(out, "x"));
  execFileSync("unzip", ["-qo", path.join(out, "items.zip"), "-d", path.join(out, "x")]);
  console.log(id, "exported");
}
