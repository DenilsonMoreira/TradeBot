"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Swal from "sweetalert2";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type BotStatus = { mode: string; updated_at: string };
type Position = { id: string; symbol: string; status: string; quantity: number; entry_price: number; realized_pnl: number | null };
type Candle = { id: number; symbol: string; interval: string; open: string; high: string; low: string; close: string; volume: string; trades: number; open_time: string; close_time: string; is_closed: boolean };
type MarketConfig = { symbols: string[]; intervals: string[]; dashboard_refresh_seconds: number };
type Model = { id: number; dataset_id: number; algorithm: string; version: string; status: string; metrics: Record<string, number | string | null> };
type Backtest = { id: number; strategy: string; symbol: string; final_capital: string; metrics: Record<string, number | string | null> };
type AuthSession = { authenticated: boolean; email: string; csrf_token: string };
type Balance = { asset: string; free: string; locked: string };
type Account = { environment: string; balances: Balance[] };
type RiskSettings = { auto_entry_enabled: boolean; max_quote_amount_per_trade: number; max_daily_loss: number; max_open_positions: number; cooldown_minutes: number; updated_at: string };
type Signal = { id: string; symbol: string; timeframe: string; signal_type: string; price: number; confidence: number | null; strategy_name: string; details: string | null; created_at: string };
type Order = { id: string; symbol: string; side: string; order_type: string; status: string; requested_quote_amount: number; executed_quantity: number | null; executed_price: number | null; error_message: string | null; created_at: string };
type AuditEvent = { id: number; actor: string; action: string; resource: string; resource_id: string | null; details: Record<string, unknown>; created_at: string };
type Notification = { id: number; severity: string; category: string; title: string; message: string; resource_id: string | null; read_at: string | null; created_at: string };
type ResearchMarketStatus = { symbol: string; interval: string; due: boolean; available_new_candles: number; required_new_candles: number; missing_candles: number; progress_percent: number; last_evaluated_at: string | null; estimated_ready_at: string | null; dataset_id: number | null };
type ResearchAutomationStatus = { enabled: boolean; promote_qualified: boolean; evaluation_interval_seconds: number; dataset_limit: number; horizon: number; markets: ResearchMarketStatus[] };
type ResearchEvaluation = { id: number; symbol: string; interval: string; dataset_id: number | null; status: string; new_candles: number; required_candles: number; models_trained: number; recommended_algorithm: string | null; activated_algorithm: string | null; metrics_summary: Record<string, unknown>; error_message: string | null; started_at: string; completed_at: string | null };
type SoakCampaign = { id: number; status: string; budget_brl: number; reference_brl_per_usdt: number; budget_quote: number; max_quote_per_trade: number; max_loss_quote: number; duration_hours: number; symbols: string[]; started_at: string; ends_at: string; completed_at: string | null };
type SoakCandleMetric = { collected: number; expected: number; coverage_percent: number; latest_close_time: string | null; fresh: boolean };
type SoakMetrics = { elapsed_percent: number; remaining_hours: number; candles: Record<string, SoakCandleMetric>; signal_count: number; order_count: number; rejected_orders: number; realized_pnl_quote: number; open_exposure_quote: number; checks: Record<string, boolean>; approved: boolean };
type SoakStatus = { campaign: SoakCampaign | null; metrics: SoakMetrics | null };

let csrfToken = "";

class ApiError extends Error {
  retryAfter: number;

  constructor(message: string, retryAfter = 0) {
    super(message);
    this.name = "ApiError";
    this.retryAfter = retryAfter;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const response = await fetch(`${API}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(method !== "GET" && csrfToken ? { "X-CSRF-Token": csrfToken } : {}), ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const retryAfter = Number(response.headers.get("Retry-After") ?? 0);
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg ?? "Valor inválido").join(" · ")
      : typeof detail === "string" ? detail : `API respondeu ${response.status}`;
    throw new ApiError(message, Number.isFinite(retryAfter) ? retryAfter : 0);
  }
  return response.status === 204 ? undefined as T : response.json();
}

function money(value: number | string | null | undefined) {
  const number = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD" }).format(number);
}

function brl(value: number | string | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

export default function Home() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [marketConfig, setMarketConfig] = useState<MarketConfig>({ symbols: ["BTCUSDT", "ETHUSDT", "BNBUSDT"], intervals: ["15m"], dashboard_refresh_seconds: 15 });
  const [marketCandles, setMarketCandles] = useState<Record<string, Candle[]>>({});
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");
  const [selectedInterval, setSelectedInterval] = useState("15m");
  const [marketUpdating, setMarketUpdating] = useState(false);
  const [marketCheckedAt, setMarketCheckedAt] = useState<Date | null>(null);
  const [nextMarketRefresh, setNextMarketRefresh] = useState(15);
  const [models, setModels] = useState<Model[]>([]);
  const [backtests, setBacktests] = useState<Backtest[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [auth, setAuth] = useState<AuthSession | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [loginError, setLoginError] = useState("");
  const [loginRetrySeconds, setLoginRetrySeconds] = useState(0);
  const [account, setAccount] = useState<Account | null>(null);
  const [risk, setRisk] = useState<RiskSettings | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [quoteAmount, setQuoteAmount] = useState(6);
  const [orders, setOrders] = useState<Order[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [researchAutomation, setResearchAutomation] = useState<ResearchAutomationStatus | null>(null);
  const [researchEvaluations, setResearchEvaluations] = useState<ResearchEvaluation[]>([]);
  const [soakStatus, setSoakStatus] = useState<SoakStatus | null>(null);
  const [activeSection, setActiveSection] = useState("overview");

  const loadMarket = useCallback(async (symbols: string[], interval: string) => {
    if (!symbols.length) return;
    setMarketUpdating(true);
    try {
      const results = await Promise.all(symbols.map(async (symbol) => ({
        symbol,
        candles: (await request<Candle[]>(`/candles?symbol=${encodeURIComponent(symbol)}&interval=${encodeURIComponent(interval)}&limit=40&closed_only=false`)).reverse(),
      })));
      setMarketCandles(Object.fromEntries(results.map((result) => [result.symbol, result.candles])));
      setMarketCheckedAt(new Date());
      setNextMarketRefresh(marketConfig.dashboard_refresh_seconds);
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível atualizar os mercados");
    } finally {
      setMarketUpdating(false);
    }
  }, [marketConfig.dashboard_refresh_seconds]);

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const [nextStatus, nextPositions, nextMarketConfig, nextModels, nextBacktests, nextRisk, nextSignals, nextOrders, nextAuditEvents, nextNotifications, nextResearchAutomation, nextResearchEvaluations, nextSoakStatus] = await Promise.all([
        request<BotStatus>("/bot/status"),
        request<Position[]>("/positions?limit=20"),
        request<MarketConfig>("/candles/config"),
        request<Model[]>("/models?limit=20"),
        request<Backtest[]>("/backtests?limit=8"),
        request<RiskSettings>("/trading/risk-settings"),
        request<Signal[]>("/signals?limit=8"),
        request<Order[]>("/orders?limit=20"),
        request<AuditEvent[]>("/audit-events?limit=12"),
        request<Notification[]>("/notifications?limit=12"),
        request<ResearchAutomationStatus>("/research/automation/status"),
        request<ResearchEvaluation[]>("/research/evaluations?limit=12"),
        request<SoakStatus>("/testnet/soak"),
      ]);
      setStatus(nextStatus);
      setPositions(nextPositions);
      setMarketConfig(nextMarketConfig);
      setSelectedSymbol((current) => nextMarketConfig.symbols.includes(current) ? current : nextMarketConfig.symbols[0] ?? "BTCUSDT");
      setSelectedInterval((current) => nextMarketConfig.intervals.includes(current) ? current : nextMarketConfig.intervals[0] ?? "15m");
      setModels(nextModels);
      setBacktests(nextBacktests);
      setRisk(nextRisk);
      setSignals(nextSignals);
      setOrders(nextOrders);
      setAuditEvents(nextAuditEvents);
      setNotifications(nextNotifications);
      setResearchAutomation(nextResearchAutomation);
      setResearchEvaluations(nextResearchEvaluations);
      setSoakStatus(nextSoakStatus);
      void request<Account>("/account/balance").then(setAccount).catch(() => setAccount(null));
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

  useEffect(() => {
    if (!auth) return;
    const initial = window.setTimeout(() => {
      void loadMarket(marketConfig.symbols, selectedInterval);
    }, 0);
    const timer = window.setInterval(() => {
      void loadMarket(marketConfig.symbols, selectedInterval);
    }, marketConfig.dashboard_refresh_seconds * 1000);
    return () => { window.clearTimeout(initial); window.clearInterval(timer); };
  }, [auth, loadMarket, marketConfig.dashboard_refresh_seconds, marketConfig.symbols, selectedInterval]);

  useEffect(() => {
    if (!auth) return;
    const timer = window.setInterval(() => setNextMarketRefresh((seconds) => Math.max(0, seconds - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [auth]);

  useEffect(() => {
    if (loginRetrySeconds <= 0) return;
    const timer = window.setInterval(() => {
      setLoginRetrySeconds((seconds) => Math.max(0, seconds - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [loginRetrySeconds]);

  useEffect(() => {
    const sectionIds = ["overview", "soak", "market", "operations", "orders", "positions", "notifications", "audit", "research"];
    const selectHashSection = () => {
      const section = window.location.hash.slice(1);
      if (sectionIds.includes(section)) setActiveSection(section);
    };
    selectHashSection();
    window.addEventListener("hashchange", selectHashSection);
    return () => window.removeEventListener("hashchange", selectHashSection);
  }, [auth]);

  const confirmAction = async (title: string, text: string, confirmButtonText: string, danger = false) => {
    const result = await Swal.fire({
      title,
      text,
      icon: danger ? "warning" : "question",
      showCancelButton: true,
      confirmButtonText,
      cancelButtonText: "Cancelar",
      confirmButtonColor: danger ? "#d94f56" : "#2da982",
      cancelButtonColor: "#344049",
      background: "#10151b",
      color: "#eef5f2",
      reverseButtons: true,
    });
    return result.isConfirmed;
  };

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
      if (cause instanceof ApiError && cause.retryAfter > 0) setLoginRetrySeconds(cause.retryAfter);
      setLoginError(cause instanceof Error ? cause.message : "Falha na autenticação");
    }
  };

  const logout = async () => {
    await request("/auth/logout", { method: "POST" });
    csrfToken = "";
    setAuth(null);
  };

  const emergencyStop = async () => {
    if (!await confirmAction("Parar o bot?", "Novas entradas serão bloqueadas imediatamente.", "Parar agora", true)) return;
    await runOperation("Parada de emergência", () => request("/bot/emergency-stop", { method: "POST" }));
  };

  const runOperation = async (label: string, action: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await action();
      await load();
      await Swal.fire({ title: "Concluído", text: `${label} concluída com sucesso.`, icon: "success", background: "#10151b", color: "#eef5f2", confirmButtonColor: "#2da982" });
    }
    catch (cause) {
      await Swal.fire({ title: `Falha em ${label.toLowerCase()}`, text: cause instanceof Error ? cause.message : "Não foi possível concluir a operação.", icon: "error", background: "#10151b", color: "#eef5f2", confirmButtonColor: "#d94f56" });
    }
    finally { setBusy(false); }
  };

  const changeMode = async (mode: string) => {
    const warning = mode === "TESTNET_TRADING" ? "Ativar execução de ordens na Binance Testnet?" : `Alterar o bot para ${mode}?`;
    if (!await confirmAction("Alterar modo operacional?", warning, "Confirmar alteração", mode === "TESTNET_TRADING")) return;
    await runOperation("Alteração do modo", () => request("/bot/status", { method: "PUT", body: JSON.stringify({ mode, confirmation: mode === "TESTNET_TRADING" ? "ATIVAR TESTNET" : undefined }) }));
  };

  const saveRisk = async () => {
    if (!risk) return;
    const summary = `Máximo por trade: ${money(risk.max_quote_amount_per_trade)} · perda diária: ${money(risk.max_daily_loss)} · cooldown: ${risk.cooldown_minutes} min.`;
    if (!await confirmAction("Salvar limites de risco?", summary, "Salvar limites", risk.auto_entry_enabled)) return;
    await runOperation("Configuração de risco", () => request("/trading/risk-settings", { method: "PUT", body: JSON.stringify({ auto_entry_enabled: risk.auto_entry_enabled, max_quote_amount_per_trade: risk.max_quote_amount_per_trade, max_daily_loss: risk.max_daily_loss, max_open_positions: risk.max_open_positions, cooldown_minutes: risk.cooldown_minutes, confirmation: risk.auto_entry_enabled ? "ATIVAR ENTRADA AUTOMATICA" : undefined }) }));
  };

  const manualBuy = async () => {
    if (!await confirmAction("Comprar BTC na Testnet?", `A ordem usará ${money(quoteAmount)} do saldo simulado.`, "Comprar BTC")) return;
    await runOperation("Compra Testnet", () => request("/trading/manual-buy", { method: "POST", body: JSON.stringify({ quote_amount: quoteAmount, confirmation: "COMPRAR BTC TESTNET" }) }));
  };

  const manualSell = async () => {
    if (!await confirmAction("Vender posição Testnet?", "A posição BTC aberta será encerrada pelo preço de mercado simulado.", "Vender posição", true)) return;
    await runOperation("Venda Testnet", () => request("/trading/manual-sell", { method: "POST", body: JSON.stringify({ confirmation: "VENDER BTC TESTNET" }) }));
  };

  const startSoakCampaign = async () => {
    if (!await confirmAction("Iniciar teste contínuo de R$ 500?", "Serão 7 dias de observação na Testnet, com teto de 6 USDT por compra e sem ativar entradas automáticas.", "Iniciar teste")) return;
    await runOperation("Campanha Testnet", () => request("/testnet/soak/start", { method: "POST", body: JSON.stringify({ confirmation: "INICIAR TESTE R$ 500", duration_hours: 168 }) }));
  };

  const markNotificationRead = async (id: number) => {
    await request(`/notifications/${id}/read`, { method: "POST" });
    setNotifications((current) => current.map((item) => item.id === id ? { ...item, read_at: new Date().toISOString() } : item));
  };

  const markAllNotificationsRead = async () => {
    await request("/notifications/read-all", { method: "POST" });
    setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })));
  };

  const candles = useMemo(() => marketCandles[selectedSymbol] ?? [], [marketCandles, selectedSymbol]);
  const lastCandle = candles.at(-1);
  const lastPrice = lastCandle?.close;
  const activePositions = positions.filter((item) => item.status === "OPEN");
  const realized = positions.reduce((total, item) => total + Number(item.realized_pnl ?? 0), 0);
  const activeModel = models.find((item) => item.status === "ACTIVE");
  const candleChart = useMemo(() => {
    if (!candles.length) return [];
    const min = Math.min(...candles.map((item) => Number(item.low)));
    const max = Math.max(...candles.map((item) => Number(item.high)));
    const span = max - min || 1;
    const y = (value: number) => 94 - ((value - min) / span) * 88;
    const step = 100 / candles.length;
    return candles.map((item, index) => {
      const open = Number(item.open); const close = Number(item.close);
      return { id: item.id, x: step * index + step / 2, width: Math.max(0.7, step * 0.58), high: y(Number(item.high)), low: y(Number(item.low)), open: y(open), close: y(close), up: close >= open };
    });
  }, [candles]);

  const candleChange = lastCandle ? ((Number(lastCandle.close) - Number(lastCandle.open)) / Number(lastCandle.open)) * 100 : 0;
  const candleTimeLabels = useMemo(() => {
    if (!candles.length) return [];
    const labelCount = Math.min(5, candles.length);
    const indexes = Array.from({ length: labelCount }, (_, index) => Math.round((index / Math.max(labelCount - 1, 1)) * (candles.length - 1)));
    return indexes.map((index) => ({
      id: candles[index].id,
      label: new Date(candles[index].open_time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
    }));
  }, [candles]);
  const queryPeriod = candles.length ? `${new Date(candles[0].open_time).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })} → ${new Date(candles.at(-1)!.close_time).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}` : "Aguardando dados";
  const researchCandidates = useMemo(() => (researchAutomation?.markets ?? []).map((market) => ({
    market,
    model: models
      .filter((item) => item.dataset_id === market.dataset_id && item.algorithm !== "baseline")
      .sort((first, second) => Number(second.metrics.walk_forward_return ?? -1) - Number(first.metrics.walk_forward_return ?? -1))[0],
  })), [models, researchAutomation]);

  if (authChecking) return <main className="auth-shell"><div className="auth-card"><span className="brand-mark">TB</span><p>Validando sessão segura…</p></div></main>;

  if (!auth) return <main className="auth-shell"><form className="auth-card" onSubmit={(event) => void login(event)}><span className="brand-mark">TB</span><div><p className="eyebrow">Acesso protegido</p><h1>TradeBrain</h1><p className="auth-copy">Entre com as credenciais do operador e o código de seis dígitos do seu autenticador.</p></div><label>E-mail<input name="email" type="email" autoComplete="username" required disabled={loginRetrySeconds > 0} /></label><label>Senha<input name="password" type="password" autoComplete="current-password" minLength={12} required disabled={loginRetrySeconds > 0} /></label><label>Código autenticador<input name="totp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} required disabled={loginRetrySeconds > 0} /></label>{loginError && <p className="auth-error" role="alert">{loginError}{loginRetrySeconds > 0 && <> Tente novamente em {Math.ceil(loginRetrySeconds / 60)} min.</>}</p>}<button type="submit" disabled={loginRetrySeconds > 0}>{loginRetrySeconds > 0 ? `Aguarde ${Math.ceil(loginRetrySeconds / 60)} min` : "Entrar com segurança"}</button><small>O acesso expira automaticamente após o período configurado.</small></form></main>;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">TB</span><div><strong>TradeBrain</strong><small>Quantitative desk</small></div></div>
        <nav aria-label="Navegação principal">
          {[{ id: "overview", label: "Visão geral" }, { id: "soak", label: "Teste R$ 500" }, { id: "market", label: "Mercado" }, { id: "operations", label: "Operação" }, { id: "orders", label: "Compras e vendas" }, { id: "positions", label: "Posições" }, { id: "notifications", label: "Notificações" }, { id: "audit", label: "Auditoria" }, { id: "research", label: "Pesquisa & IA" }].map((item) => <a key={item.id} className={activeSection === item.id ? "active" : ""} href={`#${item.id}`} aria-current={activeSection === item.id ? "page" : undefined} onClick={() => setActiveSection(item.id)}>{item.label}</a>)}
        </nav>
        <div className="sidebar-foot"><span className={`pulse ${error ? "danger" : ""}`} />{error ? "API desconectada" : "Binance Testnet"}</div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><p className="eyebrow">Centro de operações</p><h1>Bom dia, Denilson.</h1></div>
          <div className="top-actions"><a className="notification-link" href="#notifications" aria-label={`${notifications.filter((item) => !item.read_at).length} notificações não lidas`}>Alertas <b>{notifications.filter((item) => !item.read_at).length}</b></a><span className="operator">{auth.email}</span><button className="ghost" onClick={() => void Promise.all([load(), loadMarket(marketConfig.symbols, selectedInterval)])} disabled={busy || marketUpdating}>{busy || marketUpdating ? "Atualizando…" : "Atualizar"}</button><button className="ghost" onClick={() => void logout()}>Sair</button><button className="emergency" onClick={() => void emergencyStop()}>Parada de emergência</button></div>
        </header>

        {error && <div className="notice"><strong>Conecte a API local.</strong><span>{error} · endereço esperado: {API}</span></div>}
        <section className="daily-summary" id="daily" aria-label="Resumo operacional do dia">
          <div><p className="eyebrow">Resumo de hoje</p><strong>{status?.mode === "TESTNET_TRADING" ? "Operação Testnet ativa" : status?.mode === "MONITOR" ? "Mercado em monitoramento" : "Bot sem novas entradas"}</strong></div>
          <dl>
            <div><dt>P&amp;L</dt><dd className={realized >= 0 ? "positive" : "negative"}>{money(realized)}</dd></div>
            <div><dt>Em aberto</dt><dd>{activePositions.length}</dd></div>
            <div><dt>Modelo</dt><dd>{activeModel?.algorithm.replaceAll("_", " ") ?? "—"}</dd></div>
          </dl>
          <button className="summary-refresh" onClick={() => void Promise.all([load(), loadMarket(marketConfig.symbols, selectedInterval)])} disabled={busy || marketUpdating} aria-label="Atualizar dados do painel">{busy || marketUpdating ? "Atualizando…" : "Atualizar agora"}</button>
        </section>

        <section className="panel soak-panel" id="soak">
          <div className="panel-title"><div><p className="eyebrow">Validação operacional contínua</p><h3>Campanha Testnet · referência de R$ 500</h3></div><span className={soakStatus?.campaign?.status === "RUNNING" ? "positive" : "muted"}>{soakStatus?.campaign?.status === "RUNNING" ? "Em observação" : soakStatus?.campaign ? soakStatus.campaign.status : "Não iniciada"}</span></div>
          {!soakStatus?.campaign || !soakStatus.metrics ? <div className="soak-empty"><p>Nenhuma campanha foi iniciada. O teste acompanha dados, sinais e limites por 7 dias sem habilitar compras automáticas.</p><button onClick={() => void startSoakCampaign()} disabled={busy}>Iniciar teste seguro</button></div> : <>
            <p className="panel-explanation">O orçamento é uma referência experimental: {brl(soakStatus.campaign.budget_brl)} ÷ R$ {soakStatus.campaign.reference_brl_per_usdt.toFixed(2)}/USDT = {money(soakStatus.campaign.budget_quote)}. Não é uma cotação cambial ao vivo e não representa dinheiro real.</p>
            <div className="soak-summary">
              <div><small>Período</small><strong>{new Date(soakStatus.campaign.started_at).toLocaleString("pt-BR")} → {new Date(soakStatus.campaign.ends_at).toLocaleString("pt-BR")}</strong></div>
              <div><small>Progresso temporal</small><strong>{soakStatus.metrics.elapsed_percent.toFixed(2)}%</strong><span>{soakStatus.metrics.remaining_hours.toFixed(1)} h restantes</span></div>
              <div><small>Limites adicionais</small><strong>{money(soakStatus.campaign.max_quote_per_trade)} / compra</strong><span>perda máxima {money(soakStatus.campaign.max_loss_quote)}</span></div>
              <div><small>Atividade observada</small><strong>{soakStatus.metrics.signal_count} sinais · {soakStatus.metrics.order_count} ordens</strong><span>P&amp;L {money(soakStatus.metrics.realized_pnl_quote)} · exposição {money(soakStatus.metrics.open_exposure_quote)}</span></div>
            </div>
            <div className="progress-track soak-progress"><span style={{ width: `${soakStatus.metrics.elapsed_percent}%` }} /></div>
            <div className="soak-candles">{Object.entries(soakStatus.metrics.candles).map(([symbol, metric]) => <article key={symbol}><div><strong>{symbol}</strong><span className={metric.fresh ? "positive" : "negative"}>{metric.fresh ? "Feed atual" : "Feed atrasado"}</span></div><b>{metric.collected} <small>/ {metric.expected} candles 15m</small></b><div className="progress-track"><span style={{ width: `${metric.coverage_percent}%` }} /></div><small>{metric.coverage_percent.toFixed(2)}% da meta · último fechamento {metric.latest_close_time ? new Date(metric.latest_close_time).toLocaleString("pt-BR") : "indisponível"}</small></article>)}</div>
            <div className="soak-checks">{[
              ["automatic_entries_disabled", "Entrada automática continua desativada"],
              ["order_limits_respected", "Ordens respeitam 6 USDT"],
              ["exposure_within_budget", "Exposição dentro do orçamento"],
              ["loss_within_limit", "Perda dentro do limite"],
              ["no_rejected_orders", "Nenhuma ordem rejeitada"],
              ["feeds_fresh", "Feeds dos três mercados atuais"],
              ["candle_coverage", "Cobertura mínima de 95%"],
              ["duration_complete", "Sete dias concluídos"],
            ].map(([key, label]) => <span key={key} className={soakStatus.metrics!.checks[key] ? "passed" : "pending"}>{soakStatus.metrics!.checks[key] ? "✓" : "○"} {label}</span>)}</div>
          </>}
        </section>

        <section className="operations-grid" id="operations">
          <article className="panel control-panel"><div className="panel-title"><div><p className="eyebrow">Controle seguro</p><h3>Operação Testnet</h3></div><span>Confirmação obrigatória</span></div>
            <div className="mode-control"><span>Modo atual: <b>{status?.mode ?? "—"}</b></span><div><button onClick={() => void changeMode("OFF")} disabled={busy || status?.mode === "OFF"}>OFF</button><button onClick={() => void changeMode("MONITOR")} disabled={busy || status?.mode === "MONITOR"}>Monitor</button><button className="trade-mode" onClick={() => void changeMode("TESTNET_TRADING")} disabled={busy || status?.mode === "TESTNET_TRADING"}>Testnet trading</button></div></div>
            <div className="manual-trade"><label>Valor da compra (USDT)<input type="number" min="6" max="20" step="1" value={quoteAmount} onChange={(event) => setQuoteAmount(Math.min(20, Math.max(6, Number(event.target.value))))} /></label><button className="buy" onClick={() => void manualBuy()} disabled={busy || status?.mode !== "TESTNET_TRADING"}>Comprar BTC</button><button className="sell" onClick={() => void manualSell()} disabled={busy || status?.mode !== "TESTNET_TRADING" || !activePositions.length}>Vender posição</button></div>
            <p className="safety-copy">Ordens limitadas a US$ 6–20 para manter a saída acima do mínimo nocional do BTCUSDT na Binance Spot Testnet.</p>
          </article>

          <article className="panel risk-panel"><div className="panel-title"><div><p className="eyebrow">Proteção operacional</p><h3>Limites de risco</h3></div><span>{risk?.auto_entry_enabled ? "Entrada automática ativa" : "Entrada automática bloqueada"}</span></div><p className="panel-explanation">Esses valores limitam novas entradas. Para testar uma banca de referência de R$ 500, comece com 6 USDT por operação. A execução permanece em USDT e apenas uma posição pode ficar aberta.</p>{risk && <div className="risk-form"><label>Máximo por operação (USDT)<input type="number" min="6" max="20" step="1" value={risk.max_quote_amount_per_trade} onChange={(event) => setRisk({ ...risk, max_quote_amount_per_trade: Number(event.target.value) })} /><small>Permitido: US$ 6–20. A ordem automática usa exatamente este valor.</small></label><label>Perda máxima por dia (USDT)<input type="number" min="1" max="500" step="1" value={risk.max_daily_loss} onChange={(event) => setRisk({ ...risk, max_daily_loss: Number(event.target.value) })} /><small>Ao atingir o valor, novas entradas são bloqueadas.</small></label><label>Intervalo entre operações<input type="number" min="1" max="1440" value={risk.cooldown_minutes} onChange={(event) => setRisk({ ...risk, cooldown_minutes: Number(event.target.value) })} /><small>Em minutos, de 1 a 1.440.</small></label><div className="risk-locked"><span>Posições simultâneas</span><strong>{risk.max_open_positions}</strong><small>Limite de segurança fixo nesta fase.</small></div><label className="check"><input type="checkbox" checked={risk.auto_entry_enabled} onChange={(event) => setRisk({ ...risk, auto_entry_enabled: event.target.checked })} />Permitir entrada automática dentro desses limites</label><button onClick={() => void saveRisk()} disabled={busy}>Revisar e salvar</button></div>}</article>
        </section>

        <section className="content-grid account-signals">
          <article className="panel"><div className="panel-title"><div><p className="eyebrow">Carteira simulada</p><h3>Saldos da Binance Testnet</h3></div><span>{account?.environment === "testnet" ? "Sem dinheiro real" : "Indisponível"}</span></div><p className="panel-explanation">Valores fictícios fornecidos pela Binance para testar compras e vendas. “Disponível” pode ser usado; “bloqueado” está reservado em ordens abertas.</p><div className="balance-grid">{account?.balances.length ? account.balances.map((balance) => <div key={balance.asset}><strong>{balance.asset}</strong><span>{Number(balance.free).toLocaleString("pt-BR", { maximumFractionDigits: 8 })}</span><small>Disponível</small>{Number(balance.locked) > 0 && <em>{Number(balance.locked).toLocaleString("pt-BR", { maximumFractionDigits: 8 })} bloqueado</em>}</div>) : <p className="empty-inline">A carteira Testnet não retornou saldos. Verifique a chave da Binance Testnet.</p>}</div></article>
          <article className="panel"><div className="panel-title"><div><p className="eyebrow">Leitura das estratégias</p><h3>Sinais recentes</h3></div><span>{signals.length} registros</span></div><p className="panel-explanation">BUY sugere compra, SELL sugere venda e HOLD recomenda aguardar. Um sinal nunca envia uma ordem sozinho.</p><div className="signal-list">{signals.length ? signals.slice(0, 5).map((signal) => <div key={signal.id}><span className={`signal-type ${signal.signal_type.toLowerCase()}`}>{signal.signal_type === "BUY" ? "COMPRA" : signal.signal_type === "SELL" ? "VENDA" : "AGUARDAR"}</span><p><b>{signal.symbol} · {signal.timeframe}</b><span>{money(signal.price)} · {signal.confidence == null ? "confiança não informada" : `${signal.confidence}% de confiança`}</span><small>{signal.strategy_name} · {new Date(signal.created_at).toLocaleString("pt-BR")}</small>{signal.details && <small>{signal.details}</small>}</p></div>) : <p className="empty-inline">Nenhuma estratégia gerou sinal até agora.</p>}</div></article>
        </section>

        <section className="panel orders-panel" id="orders"><div className="panel-title"><div><p className="eyebrow">Histórico de execução</p><h3>Compras e vendas Testnet</h3></div><span>{orders.length} ordens recentes</span></div><p className="panel-explanation">Registro das ordens enviadas à Binance Testnet. BUY é compra e SELL é venda; nenhuma linha representa dinheiro real.</p><div className="table-wrap"><table><thead><tr><th>Data</th><th>Ação</th><th>Ativo</th><th>Status</th><th>Valor solicitado</th><th>Quantidade executada</th><th>Preço médio</th></tr></thead><tbody>{orders.length ? orders.map((order) => <tr key={order.id}><td>{new Date(order.created_at).toLocaleString("pt-BR")}</td><td><span className={`order-side ${order.side.toLowerCase()}`}>{order.side === "BUY" ? "COMPRA" : "VENDA"}</span></td><td><b>{order.symbol}</b></td><td>{order.status}</td><td>{money(order.requested_quote_amount)}</td><td>{order.executed_quantity == null ? "—" : Number(order.executed_quantity).toFixed(8)}</td><td>{order.executed_price == null ? "—" : money(order.executed_price)}</td></tr>) : <tr><td colSpan={7} className="empty">Nenhuma compra ou venda foi executada na Testnet.</td></tr>}</tbody></table></div></section>

        <section className="panel audit-panel" id="audit"><div className="panel-title"><div><p className="eyebrow">Rastreabilidade</p><h3>Auditoria operacional</h3></div><span>{auditEvents.length} eventos recentes</span></div><div className="audit-list">{auditEvents.length ? auditEvents.map((event) => <div className="audit-row" key={event.id}><span className="audit-dot" /><div><strong>{event.action.replaceAll("_", " ")}</strong><small>{event.actor} · {event.resource}{event.resource_id ? ` #${event.resource_id}` : ""}</small></div><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString("pt-BR")}</time></div>) : <p className="empty-inline">As próximas ações operacionais aparecerão aqui.</p>}</div></section>

        <section className="panel notifications-panel" id="notifications"><div className="panel-title"><div><p className="eyebrow">Central interna</p><h3>Notificações operacionais</h3></div><button className="text-button" onClick={() => void markAllNotificationsRead()} disabled={!notifications.some((item) => !item.read_at)}>Marcar todas como lidas</button></div><div className="notifications-list">{notifications.length ? notifications.map((item) => <article className={`notification-item ${item.read_at ? "read" : "unread"}`} key={item.id}><span className={`severity ${item.severity.toLowerCase()}`}>{item.severity}</span><div><strong>{item.title}</strong><p>{item.message}</p><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("pt-BR")}</time></div>{!item.read_at && <button onClick={() => void markNotificationRead(item.id)}>Marcar como lida</button>}</article>) : <p className="empty-inline">Nenhuma notificação operacional.</p>}</div></section>

        <section className="hero-grid" id="overview">
          <article className="market-card" id="market">
            <div className="market-symbols" aria-label="Mercados configurados">{marketConfig.symbols.map((symbol) => { const item = marketCandles[symbol]?.at(-1); const change = item ? ((Number(item.close) - Number(item.open)) / Number(item.open)) * 100 : 0; return <button key={symbol} className={selectedSymbol === symbol ? "active" : ""} onClick={() => setSelectedSymbol(symbol)}><span>{symbol.replace("USDT", " / USDT")}</span><strong>{item ? money(item.close) : "—"}</strong><small className={change >= 0 ? "positive" : "negative"}>{item ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}% no candle` : "Aguardando dados"}</small></button>; })}</div>
            <div className="card-head"><div><p className="eyebrow">{selectedSymbol.replace("USDT", " / USDT")} · {selectedInterval}</p><h2>{lastPrice ? money(lastPrice) : "—"}</h2><small className={candleChange >= 0 ? "positive" : "negative"}>{lastCandle ? `${candleChange >= 0 ? "+" : ""}${candleChange.toFixed(2)}% neste candle` : ""}</small></div><div className="market-live"><span className={`live-pill ${marketUpdating ? "updating" : ""}`}>{marketUpdating ? "Atualizando…" : "Monitoramento ativo"}</span><small>Próxima consulta em {nextMarketRefresh}s</small></div></div>
            <div className="chart-wrap candlestick-chart" aria-label={`Candles recentes de ${selectedSymbol}`}>
              {candleChart.length ? <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img">{candleChart.map((item) => <g key={item.id} className={item.up ? "candle-up" : "candle-down"}><line x1={item.x} y1={item.high} x2={item.x} y2={item.low}/><rect x={item.x - item.width / 2} y={Math.min(item.open, item.close)} width={item.width} height={Math.max(1, Math.abs(item.close - item.open))}/></g>)}</svg> : <div className="empty-chart">Aguardando candles de {selectedSymbol}</div>}
            </div>
            <div className="chart-time-axis" aria-label="Horários dos candles">{candleTimeLabels.map((item) => <time key={item.id}>{item.label}</time>)}</div>
            <div className="query-period"><span>Período consultado</span><strong>{queryPeriod}</strong><small>{candles.length} candles · intervalo {selectedInterval} · incluindo candle em formação</small></div>
            <div className="market-meta"><span><small>Último candle</small>{lastCandle ? new Date(lastCandle.open_time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "—"}</span><span><small>Status</small>{lastCandle?.is_closed ? "Fechado" : "Em formação"}</span><span><small>Verificado</small>{marketCheckedAt ? marketCheckedAt.toLocaleTimeString("pt-BR") : "—"}</span><span><small>Fonte</small>Binance Testnet</span></div>
            <div className="candle-table"><div className="candle-table-title"><strong>Candles recentes</strong><span>OHLC · volume · negócios</span></div><div className="table-wrap"><table><thead><tr><th>Horário</th><th>Abertura</th><th>Máxima</th><th>Mínima</th><th>Fechamento</th><th>Volume</th><th>Negócios</th><th>Status</th></tr></thead><tbody>{candles.slice(-8).reverse().map((candle) => <tr key={candle.id}><td>{new Date(candle.open_time).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</td><td>{money(candle.open)}</td><td>{money(candle.high)}</td><td>{money(candle.low)}</td><td className={Number(candle.close) >= Number(candle.open) ? "positive" : "negative"}>{money(candle.close)}</td><td>{Number(candle.volume).toLocaleString("pt-BR", { maximumFractionDigits: 4 })}</td><td>{candle.trades.toLocaleString("pt-BR")}</td><td><span className={`candle-state ${candle.is_closed ? "closed" : "forming"}`}>{candle.is_closed ? "Fechado" : "Em formação"}</span></td></tr>)}</tbody></table></div></div>
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

          <article className="panel intelligence"><div className="panel-title"><div><p className="eyebrow">Inteligência</p><h3>Model registry</h3></div><span>{models.length} modelos</span></div>
            <div className="model-focus"><span className="model-icon">AI</span><div><small>Modelo ativo</small><strong>{activeModel?.algorithm.replaceAll("_", " ") ?? "Nenhum promovido"}</strong><p>{activeModel ? `Retorno teste: ${Number(activeModel.metrics.strategy_return ?? 0).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 2 })}` : "Promova um candidato após revisar as métricas."}</p></div></div>
            <div className="model-list">{models.slice(0, 4).map((model) => <div key={model.id}><span>{model.algorithm.replaceAll("_", " ")}</span><b>{model.status}</b></div>)}</div>
          </article>
        </section>

        <section className="panel research-monitor" id="research">
          <div className="panel-title"><div><p className="eyebrow">Pesquisa automatizada</p><h3>Próxima avaliação quantitativa</h3></div><span className={researchAutomation?.enabled ? "positive" : "muted"}>{researchAutomation?.enabled ? "Monitor ativo" : "Monitor desativado"}</span></div>
          <p className="panel-explanation">Uma nova rodada só começa quando o período de teste estiver totalmente inédito. A promoção automática permanece {researchAutomation?.promote_qualified ? "habilitada" : "desabilitada"}.</p>
          <div className="research-progress-grid">
            {(researchAutomation?.markets ?? []).map((market) => <article className="research-progress-card" key={`${market.symbol}-${market.interval}`}>
              <div><strong>{market.symbol}</strong><span>{market.interval} · horizonte {researchAutomation?.horizon ?? 4} candles</span></div>
              <b>{market.available_new_candles} <small>/ {market.required_new_candles} candles</small></b>
              <div className="progress-track" role="progressbar" aria-label={`Progresso de ${market.symbol}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(market.progress_percent)}><span style={{ width: `${market.progress_percent}%` }} /></div>
              <footer><span>{market.missing_candles ? `Faltam ${market.missing_candles}` : "Janela pronta"}</span><time>{market.estimated_ready_at ? `Estimativa ${new Date(market.estimated_ready_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })}` : "Aguardando histórico"}</time></footer>
            </article>)}
          </div>
          <div className="research-candidates"><div className="research-subtitle"><strong>Melhor candidato atual por mercado</strong><span>Retornos líquidos, com custos</span></div>
            <div className="research-candidate-grid">{researchCandidates.map(({ market, model }) => <article key={market.symbol}>
              <small>{market.symbol}</small><strong>{model?.algorithm.replaceAll("_", " ") ?? "Sem candidato"}</strong>
              {model ? <dl><div><dt>Teste final</dt><dd className={Number(model.metrics.strategy_return ?? 0) >= 0 ? "positive" : "negative"}>{Number(model.metrics.strategy_return ?? 0).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 2 })}</dd></div><div><dt>Walk-forward</dt><dd className={Number(model.metrics.walk_forward_return ?? 0) >= 0 ? "positive" : "negative"}>{Number(model.metrics.walk_forward_return ?? 0).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 2 })}</dd></div><div><dt>Folds lucrativos</dt><dd>{model.metrics.walk_forward_profitable_folds ?? 0}/{model.metrics.walk_forward_folds ?? 0}</dd></div></dl> : <p>Aguardando modelos avaliados.</p>}
            </article>)}</div>
          </div>
          <div className="research-history"><div className="research-subtitle"><strong>Histórico de reavaliações automáticas</strong><span>{researchEvaluations.length} execuções registradas</span></div>
            {researchEvaluations.length ? <div className="table-wrap"><table><thead><tr><th>Início</th><th>Mercado</th><th>Status</th><th>Modelos</th><th>Resultado</th></tr></thead><tbody>{researchEvaluations.map((run) => <tr key={run.id}><td>{new Date(run.started_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</td><td><b>{run.symbol}</b> · {run.interval}</td><td><span className={`evaluation-status ${run.status.toLowerCase()}`}>{run.status === "COMPLETED" ? "Concluída" : run.status === "FAILED" ? "Falhou" : run.status === "SKIPPED" ? "Ignorada" : "Executando"}</span></td><td>{run.models_trained}</td><td>{run.error_message ?? (run.activated_algorithm ? `${run.activated_algorithm.replaceAll("_", " ")} ativado` : run.recommended_algorithm ? `${run.recommended_algorithm.replaceAll("_", " ")} recomendado` : "Nenhum candidato aprovado")}</td></tr>)}</tbody></table></div> : <p className="empty-inline">Nenhuma reavaliação automática executada. O histórico começará quando a primeira janela inédita estiver completa.</p>}
          </div>
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
