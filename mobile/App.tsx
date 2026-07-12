import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator, Alert, Pressable, RefreshControl, SafeAreaView,
  ScrollView, StyleSheet, Text, TextInput, View,
} from 'react-native';

const API = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000';
const SESSION_KEY = 'tradebrain.operator.session';

type Session = { email: string; csrf_token: string; session_token: string };
type BotStatus = { mode: string; updated_at: string };
type Position = { id: string; symbol: string; status: string; quantity: number; entry_price: number; realized_pnl: number | null };
type Model = { id: number; algorithm: string; status: string; metrics: Record<string, number | string | null> };

async function api<T>(path: string, session?: Session, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { Authorization: `Bearer ${session.session_token}` } : {}),
      ...(session && init?.method && init.method !== 'GET' ? { 'X-CSRF-Token': session.csrf_token } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `API respondeu ${response.status}`);
  }
  return response.status === 204 ? undefined as T : response.json();
}

function money(value: number | string | null | undefined) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' }).format(Number(value ?? 0));
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totp, setTotp] = useState('');
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [models, setModels] = useState<Model[]>([]);

  const load = useCallback(async (active: Session) => {
    setBusy(true); setError('');
    try {
      const [nextStatus, nextPositions, nextModels] = await Promise.all([
        api<BotStatus>('/bot/status', active),
        api<Position[]>('/positions?limit=20', active),
        api<Model[]>('/models?limit=20', active),
      ]);
      setStatus(nextStatus); setPositions(nextPositions); setModels(nextModels);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Falha ao carregar dados';
      setError(message);
      if (message.toLowerCase().includes('sessão')) { await SecureStore.deleteItemAsync(SESSION_KEY); setSession(null); }
    } finally { setBusy(false); }
  }, []);

  useEffect(() => {
    void SecureStore.getItemAsync(SESSION_KEY).then(async (stored) => {
      if (!stored) return;
      const restored = JSON.parse(stored) as Session;
      try {
        await api('/auth/session', restored);
        setSession(restored);
        await load(restored);
      } catch { await SecureStore.deleteItemAsync(SESSION_KEY); }
    }).finally(() => setChecking(false));
  }, [load]);

  const login = async () => {
    setBusy(true); setError('');
    try {
      const next = await api<Session>('/auth/mobile-login', undefined, {
        method: 'POST', body: JSON.stringify({ email, password, totp_code: totp }),
      });
      await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(next));
      setSession(next); setPassword(''); setTotp('');
      await load(next);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Falha no login'); }
    finally { setBusy(false); }
  };

  const logout = async () => {
    await SecureStore.deleteItemAsync(SESSION_KEY);
    setSession(null); setStatus(null); setPositions([]); setModels([]);
  };

  const emergencyStop = () => Alert.alert(
    'Parada de emergência', 'Desligar o bot e bloquear novas entradas?',
    [{ text: 'Cancelar', style: 'cancel' }, { text: 'Parar bot', style: 'destructive', onPress: async () => {
      if (!session) return;
      try { await api('/bot/emergency-stop', session, { method: 'POST' }); await load(session); }
      catch (cause) { Alert.alert('Falha', cause instanceof Error ? cause.message : 'Não foi possível parar o bot'); }
    }}],
  );

  const openPositions = positions.filter((item) => item.status === 'OPEN');
  const realized = positions.reduce((sum, item) => sum + Number(item.realized_pnl ?? 0), 0);
  const activeModel = useMemo(() => models.find((item) => item.status === 'ACTIVE'), [models]);

  if (checking) return <SafeAreaView style={styles.center}><ActivityIndicator color="#53e0b1" /><Text style={styles.muted}>Validando sessão segura…</Text></SafeAreaView>;

  if (!session) return (
    <SafeAreaView style={styles.authShell}>
      <StatusBar style="light" />
      <View style={styles.authCard}>
        <View style={styles.logo}><Text style={styles.logoText}>TB</Text></View>
        <View><Text style={styles.eyebrow}>ACESSO PROTEGIDO</Text><Text style={styles.title}>TradeBrain</Text><Text style={styles.copy}>Entre com a senha do operador e o código atual do autenticador.</Text></View>
        <TextInput style={styles.input} value={email} onChangeText={setEmail} placeholder="E-mail" placeholderTextColor="#66736f" autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
        <TextInput style={styles.input} value={password} onChangeText={setPassword} placeholder="Senha" placeholderTextColor="#66736f" secureTextEntry autoComplete="current-password" />
        <TextInput style={styles.input} value={totp} onChangeText={(value) => setTotp(value.replace(/\D/g, '').slice(0, 6))} placeholder="Código de 6 dígitos" placeholderTextColor="#66736f" keyboardType="number-pad" maxLength={6} />
        {!!error && <Text style={styles.error}>{error}</Text>}
        <Pressable style={[styles.primary, busy && styles.disabled]} onPress={() => void login()} disabled={busy || !email || password.length < 12 || totp.length !== 6}><Text style={styles.primaryText}>{busy ? 'Entrando…' : 'Entrar com segurança'}</Text></Pressable>
        <Text style={styles.endpoint}>API: {API}</Text>
      </View>
    </SafeAreaView>
  );

  return (
    <SafeAreaView style={styles.shell}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.content} refreshControl={<RefreshControl refreshing={busy} onRefresh={() => void load(session)} tintColor="#53e0b1" />}>
        <View style={styles.header}><View><Text style={styles.eyebrow}>CENTRO DE OPERAÇÕES</Text><Text style={styles.heading}>TradeBrain</Text><Text style={styles.muted}>{session.email}</Text></View><Pressable onPress={() => void logout()}><Text style={styles.link}>Sair</Text></Pressable></View>
        {!!error && <View style={styles.notice}><Text style={styles.error}>{error}</Text></View>}
        <View style={styles.hero}><Text style={styles.eyebrow}>STATUS OPERACIONAL</Text><Text style={[styles.mode, status?.mode !== 'OFF' && styles.positive]}>{status?.mode ?? '—'}</Text><Text style={styles.muted}>Binance Spot Testnet</Text></View>
        <View style={styles.metrics}><Metric label="P&L realizado" value={money(realized)} positive={realized >= 0} /><Metric label="Posições abertas" value={String(openPositions.length)} /><Metric label="Modelo ativo" value={activeModel?.algorithm.replaceAll('_', ' ') ?? 'Nenhum'} /></View>
        <View style={styles.panel}><Text style={styles.panelTitle}>Posições recentes</Text>{positions.slice(0, 6).map((item) => <View style={styles.row} key={item.id}><View><Text style={styles.symbol}>{item.symbol}</Text><Text style={styles.muted}>{item.status} · {Number(item.quantity).toFixed(6)}</Text></View><Text style={Number(item.realized_pnl ?? 0) >= 0 ? styles.positive : styles.negative}>{item.realized_pnl == null ? money(item.entry_price) : money(item.realized_pnl)}</Text></View>)}{!positions.length && <Text style={styles.muted}>Nenhuma posição registrada.</Text>}</View>
        <Pressable style={styles.dangerButton} onPress={emergencyStop}><Text style={styles.dangerText}>Parada de emergência</Text></Pressable>
        <Text style={styles.disclaimer}>Somente Testnet. Previsões não enviam ordens diretamente.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Metric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return <View style={styles.metric}><Text style={styles.muted}>{label}</Text><Text numberOfLines={1} style={[styles.metricValue, positive && styles.positive]}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  shell:{flex:1,backgroundColor:'#080b0f'},authShell:{flex:1,backgroundColor:'#080b0f',justifyContent:'center',padding:22},center:{flex:1,backgroundColor:'#080b0f',alignItems:'center',justifyContent:'center',gap:12},content:{padding:20,paddingBottom:42,gap:16},authCard:{gap:18,padding:24,borderWidth:1,borderColor:'#222c35',borderRadius:18,backgroundColor:'#10151b'},logo:{width:44,height:44,borderWidth:1,borderColor:'#53e0b166',borderRadius:12,alignItems:'center',justifyContent:'center'},logoText:{color:'#53e0b1',fontWeight:'800'},eyebrow:{color:'#82908c',fontSize:10,fontWeight:'700',letterSpacing:1.4},title:{color:'#eef5f2',fontSize:32,fontWeight:'700',letterSpacing:-1.2},copy:{color:'#82908c',fontSize:13,lineHeight:20,marginTop:8},input:{height:50,paddingHorizontal:14,borderWidth:1,borderColor:'#222c35',borderRadius:10,backgroundColor:'#080c10',color:'#eef5f2'},primary:{height:50,alignItems:'center',justifyContent:'center',borderRadius:10,borderWidth:1,borderColor:'#53e0b144',backgroundColor:'#53e0b116'},primaryText:{color:'#53e0b1',fontWeight:'800'},disabled:{opacity:.45},error:{color:'#ff7f84',fontSize:12},endpoint:{color:'#56635f',fontSize:10,textAlign:'center'},header:{flexDirection:'row',justifyContent:'space-between',alignItems:'center',marginBottom:4},heading:{color:'#eef5f2',fontSize:28,fontWeight:'700',letterSpacing:-1},link:{color:'#53e0b1',padding:12},muted:{color:'#82908c',fontSize:11},notice:{padding:14,borderWidth:1,borderColor:'#ff6b7044',borderRadius:11,backgroundColor:'#ff6b700c'},hero:{padding:22,borderWidth:1,borderColor:'#253039',borderRadius:16,backgroundColor:'#111820',gap:6},mode:{color:'#9aa7a3',fontSize:27,fontWeight:'700'},positive:{color:'#53e0b1'},negative:{color:'#ff6b70'},metrics:{gap:10},metric:{padding:17,borderWidth:1,borderColor:'#222c35',borderRadius:13,backgroundColor:'#10151b'},metricValue:{color:'#eef5f2',fontSize:18,fontWeight:'700',marginTop:6,textTransform:'capitalize'},panel:{padding:18,borderWidth:1,borderColor:'#222c35',borderRadius:14,backgroundColor:'#10151b',gap:4},panelTitle:{color:'#eef5f2',fontSize:17,fontWeight:'700',marginBottom:10},row:{minHeight:56,flexDirection:'row',alignItems:'center',justifyContent:'space-between',borderBottomWidth:1,borderBottomColor:'#202831',gap:12},symbol:{color:'#eef5f2',fontWeight:'700'},dangerButton:{height:52,alignItems:'center',justifyContent:'center',borderWidth:1,borderColor:'#ff6b7055',borderRadius:12,backgroundColor:'#ff6b7012'},dangerText:{color:'#ff9599',fontWeight:'800'},disclaimer:{color:'#56635f',fontSize:10,textAlign:'center'},
});
