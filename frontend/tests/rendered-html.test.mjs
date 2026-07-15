import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import test from "node:test";

const templateRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the secure TradeBrain loading shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html lang="pt-BR">/i);
  assert.match(html, /<title>TradeBrain · Quantitative Trading Desk<\/title>/i);
  assert.match(html, /class="auth-shell"/);
  assert.match(html, /Validando sessão segura/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/i);
});

test("keeps authentication and production metadata in the web application", async () => {
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /request<AuthSession>\("\/auth\/session"\)/);
  assert.match(page, /type="password"/);
  assert.match(page, /autoComplete="one-time-code"/);
  assert.match(page, /Retry-After/);
  assert.match(page, /Swal\.fire/);
  assert.match(page, /Compras e vendas Testnet/);
  assert.match(page, /Saldos da Binance Testnet/);
  assert.match(page, /\/candles\/config/);
  assert.match(page, /closed_only=false/);
  assert.match(page, /Candles recentes/);
  assert.match(page, /Período consultado/);
  assert.match(page, /chart-time-axis/);
  assert.match(page, /\/research\/automation\/status/);
  assert.match(page, /Próxima avaliação quantitativa/);
  assert.match(page, /research-progress-grid/);
  assert.match(page, /\/research\/evaluations\?limit=12/);
  assert.match(page, /Histórico de reavaliações automáticas/);
  assert.match(page, /\/testnet\/soak/);
  assert.match(page, /Campanha Testnet · referência de R\$ 500/);
  assert.match(page, /Entrada automática continua desativada/);
  assert.match(page, /addEventListener\("hashchange", selectHashSection\)/);
  assert.match(page, /aria-current=\{activeSection === item\.id \? "page" : undefined\}/);
  assert.match(layout, /title:\s*"TradeBrain · Quantitative Trading Desk"/);
  assert.match(layout, /manifest:\s*"\/manifest\.webmanifest"/);
  assert.match(layout, /themeColor:\s*"#080b0f"/);
  assert.match(packageJson, /"test":\s*"npm run build && node --test tests\/rendered-html\.test\.mjs"/);

  assert.deepEqual(await readdir(new URL("app/_sites-preview", templateRoot)), []);
});
