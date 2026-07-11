"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type BotStatus = { mode: string; updated_at: string };
type Position = { id: string; symbol: string; status: string; quantity: number; entry_price: number; realized_pnl: number | null };
type Candle = { id: number; symbol: string; interval: string; close: string; open_time: string; is_closed: boolean };
type Model = { id: number; algorithm: string; status: string; metrics: Record<string, number | string | null> };
type Backtest = { id: number; strategy: string; symbol: string; final_capital: string; metrics: Record<string, number | string | null> };
type AuthSession = { authenticated: boolean; email: string; csrf_token: string };

let csrfToken = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(method !== "GET" && csrfToken ? { "X-CSRF-Token": csrfToken } : {}), ...init?.headers },
  });
  if (!response.ok) throw new Error(`API respondeu ${response.status}`);
  return response.json();
}

function money(value: number | string | null | undefined) {
  const number = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD" }).format(number);
}

export default function Home() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [backtests, setBacktests] = useState<Backtest[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [loginError, setLoginError] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const [nextStatus, nextPositions, nextCandles, nextModels, nextBacktests] = await Promise.all([
        request<BotStatus>("/bot/status"),
        request<Position[]>("/positions?limit=20"),
        request<Candle[]>("/candles?symbol=BTCUSDT&interval=15m&limit=32&closed_only=true"),
        request<Model[]>("/models?limit=20"),
        request<Backtest[]>("/backtests?limit=8"),
      ]);
      setStatus(nextStatus);
      setPositions(nextPositions);
      setCandles(nextCandles.reverse());
      setModels(nextModels);
      setBacktests(nextBacktests);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível carregar o painel");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void request<AuthSession>("/auth/session")
      .then((session) => { csrfToken = session.csrf_token; setAuth(session); void load(); })
      .catch(() => setAuth(null))
      .finally(() => setAuthChecking(false));
  }, [load]);

  const login = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError("");
    const data = new FormData(event.currentTarget);
    try {
      const session = await request<AuthSession>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: data.get("email"), password: data.get("password"), totp_code: data.get("totp") }),
      });
      csrfToken = session.csrf_token;
      setAuth(session);
      await load();
    } catch (cause) {
      setLoginError(cause instanceof Error ? cause.message : "Falha na autenticação");
    }
  };

  const logout = async () => {
    await request("/auth/logout", { method: "POST" });
    csrfToken = "";
    setAuth(null);
  };

  const emergencyStop = async () => {
    if (!window.confirm("Desligar o bot e bloquear novas entradas?")) return;
    await request("/bot/emergency-stop", { method: "POST" });
    await load();
  };

  const lastPrice = candles.at(-1)?.close;
  const activePositions = positions.filter((item) => item.status === "OPEN");
  const realized = positions.reduce((total, item) => total + Number(item.realized_pnl ?? 0), 0);
  const activeModel = models.find((item) => item.status === "ACTIVE");
  const chart = useMemo(() => {
    const values = candles.map((item) => Number(item.close));
    if (!values.length) return "";
    const min = Math.min(...values); const max = Math.max(...values); const span = max - min || 1;
    return values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${88 - ((value - min) / span) * 72}`).join(" ");
  }, [candles]);

  if (authChecking) return <main className="auth-shell"><div className="auth-card"><span className="brand-mark">TB</span><p>Validando sessão segura…</p></div></main>;

  if (!auth) return <main className="auth-shell"><form className="auth-card" onSubmit={(event) => void login(event)}><span className="brand-mark">TB</span><div><p className="eyebrow">Acesso protegido</p><h1>TradeBrain</h1><p className="auth-copy">Entre com as credenciais do operador e o código de seis dígitos do seu autenticador.</p></div><label>E-mail<input name="email" type="email" autoComplete="username" required /></label><label>Senha<input name="password" type="password" autoComplete="current-password" minLength={12} required /></label><label>Código autenticador<input name="totp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required /></label>{loginError && <p className="auth-error" role="alert">{loginError}</p>}<button type="submit">Entrar com segurança</button><small>O acesso expira automaticamente após o período configurado.</small></form></main>;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">TB</span><div><strong>TradeBrain</strong><small>Quantitative desk</small></div></div>
        <nav aria-label="Navegação principal">
          <a className="active" href="#overview">Visão geral</a><a href="#market">Mercado</a><a href="#positions">Posições</a><a href="#research">Pesquisa & IA</a>
        </nav>
        <div className="sidebar-foot"><span className={`pulse ${error ? "danger" : ""}`} />{error ? "API desconectada" : "Binance Testnet"}</div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><p className="eyebrow">Centro de operações</p><h1>Bom dia, Denilson.</h1></div>
          <div className="top-actions"><span className="operator">{auth.email}</span><button className="ghost" onClick={() => void load()} disabled={busy}>{busy ? "Atualizando…" : "Atualizar"}</button><button className="ghost" onClick={() => void logout()}>Sair</button><button className="emergency" onClick={() => void emergencyStop()}>Parada de emergência</button></div>
        </header>

        {error && <div className="notice"><strong>Conecte a API local.</strong><span>{error} · endereço esperado: {API}</span></div>}

        <section className="daily-summary" id="daily" aria-label="Resumo operacional do dia">
          <div><p className="eyebrow">Resumo de hoje</p><strong>{status?.mode === "TESTNET_TRADING" ? "Operação Testnet ativa" : status?.mode === "MONITOR" ? "Mercado em monitoramento" : "Bot sem novas entradas"}</strong></div>
          <dl>
            <div><dt>P&amp;L</dt><dd className={realized >= 0 ? "positive" : "negative"}>{money(realized)}</dd></div>
            <div><dt>Em aberto</dt><dd>{activePositions.length}</dd></div>
            <div><dt>Modelo</dt><dd>{activeModel?.algorithm.replaceAll("_", " ") ?? "—"}</dd></div>
          </dl>
          <button className="summary-refresh" onClick={() => void load()} disabled={busy} aria-label="Atualizar dados do painel">{busy ? "Atualizando…" : "Atualizar agora"}</button>
        </section>

        <section className="hero-grid" id="overview">
          <article className="market-card" id="market">
            <div className="card-head"><div><p className="eyebrow">BTC / USDT · 15m</p><h2>{lastPrice ? money(lastPrice) : "—"}</h2></div><span className="live-pill">Mercado ao vivo</span></div>
            <div className="chart-wrap" aria-label="Histórico recente do preço do Bitcoin">
              {chart ? <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#53e0b1" stopOpacity=".35"/><stop offset="1" stopColor="#53e0b1" stopOpacity="0"/></linearGradient></defs><polygon points={`0,100 ${chart} 100,100`} fill="url(#area)"/><polyline points={chart} fill="none" stroke="#53e0b1" strokeWidth="2" vectorEffect="non-scaling-stroke"/></svg> : <div className="empty-chart">Aguardando candles</div>}
            </div>
            <div className="market-meta"><span><small>Candles</small>{candles.length}</span><span><small>Fonte</small>Binance Spot</span><span><small>Ambiente</small>Testnet</span></div>
          </article>

          <div className="metric-stack">
            <article className="metric-card"><p>Modo operacional</p><strong className={status?.mode === "OFF" ? "muted" : "positive"}>{status?.mode ?? "—"}</strong><small>Atualizado {status ? new Date(status.updated_at).toLocaleTimeString("pt-BR") : "—"}</small></article>
            <article className="metric-card"><p>Posições abertas</p><strong>{activePositions.length}</strong><small>Limites de risco ativos</small></article>
            <article className="metric-card"><p>P&amp;L realizado</p><strong className={realized >= 0 ? "positive" : "negative"}>{money(realized)}</strong><small>Histórico carregado</small></article>
          </div>
        </section>

        <section className="content-grid">
          <article className="panel" id="positions"><div className="panel-title"><div><p className="eyebrow">Execução</p><h3>Posições recentes</h3></div><span>{positions.length} registros</span></div>
            <div className="table-wrap"><table><thead><tr><th>Ativo</th><th>Status</th><th>Quantidade</th><th>Entrada</th><th>Resultado</th></tr></thead><tbody>{positions.length ? positions.slice(0, 6).map((item) => <tr key={item.id}><td><b>{item.symbol}</b></td><td><span className={`status ${item.status.toLowerCase()}`}>{item.status}</span></td><td>{Number(item.quantity).toFixed(6)}</td><td>{money(item.entry_price)}</td><td className={Number(item.realized_pnl ?? 0) >= 0 ? "positive" : "negative"}>{item.realized_pnl == null ? "—" : money(item.realized_pnl)}</td></tr>) : <tr><td colSpan={5} className="empty">Nenhuma posição registrada</td></tr>}</tbody></table></div>
          </article>

          <article className="panel intelligence" id="research"><div className="panel-title"><div><p className="eyebrow">Inteligência</p><h3>Model registry</h3></div><span>{models.length} modelos</span></div>
            <div className="model-focus"><span className="model-icon">AI</span><div><small>Modelo ativo</small><strong>{activeModel?.algorithm.replaceAll("_", " ") ?? "Nenhum promovido"}</strong><p>{activeModel ? `Retorno teste: ${Number(activeModel.metrics.strategy_return ?? 0).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 2 })}` : "Promova um candidato após revisar as métricas."}</p></div></div>
            <div className="model-list">{models.slice(0, 4).map((model) => <div key={model.id}><span>{model.algorithm.replaceAll("_", " ")}</span><b>{model.status}</b></div>)}</div>
          </article>
        </section>

        <section className="panel backtests"><div className="panel-title"><div><p className="eyebrow">Validação</p><h3>Backtests recentes</h3></div><span>Custos e slippage incluídos</span></div><div className="backtest-grid">{backtests.length ? backtests.slice(0, 4).map((run) => <div className="backtest-item" key={run.id}><small>{run.symbol} · {run.strategy}</small><strong>{money(run.final_capital)}</strong><span>{run.metrics.trade_count ?? 0} operações · retorno {Number(run.metrics.return_percent ?? 0).toFixed(2)}%</span></div>) : <p className="empty">Execute um backtest para iniciar a comparação.</p>}</div></section>
      </section>

      <nav className="mobile-nav" aria-label="Navegação móvel">
        <a href="#overview"><span aria-hidden="true">⌂</span>Início</a>
        <a href="#market"><span aria-hidden="true">⌁</span>Mercado</a>
        <a href="#positions"><span aria-hidden="true">◎</span>Posições</a>
        <a href="#research"><span aria-hidden="true">◇</span>Pesquisa</a>
      </nav>
      <button className="mobile-emergency" onClick={() => void emergencyStop()} aria-label="Acionar parada de emergência">Parar bot</button>
    </main>
  );
}
