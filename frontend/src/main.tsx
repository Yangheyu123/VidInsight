import { FormEvent, ReactNode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Download, LayoutDashboard, LogOut, Plus, RefreshCw, Settings2, Sparkles, Trash2, Users, Video as VideoIcon } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Account, api, apiDownload, clearToken, dateRange, Overview, setToken, token, Video } from "./api";
import "./styles.css";

const client = new QueryClient();
const format = new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 });
const number = (value: number | null | undefined) => value == null ? "—" : format.format(value);
const percent = (value: number | null | undefined) => value == null ? "—" : `${(value * 100).toFixed(1)}%`;

function usePeriod() {
  const [period, setPeriod] = useState<"day" | "week" | "month">("week");
  const range = useMemo(() => {
    const end = new Date(); const start = new Date(end);
    start.setDate(end.getDate() - (period === "day" ? 1 : period === "week" ? 7 : 30));
    return { start: start.toISOString(), end: end.toISOString(), period };
  }, [period]);
  return { period, setPeriod, range };
}

function Login() {
  const navigate = useNavigate(); const [email, setEmail] = useState("admin@vidinsight.local"); const [password, setPassword] = useState("ChangeMe123!");
  const login = useMutation({ mutationFn: () => api<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }), onSuccess: data => { setToken(data.access_token); navigate("/"); } });
  return <main className="login"><section className="login-card"><div className="brand-mark">V</div><h1>VidInsight</h1><p>内部短视频矩阵运营看板</p><form onSubmit={(event: FormEvent) => { event.preventDefault(); login.mutate(); }}><label>邮箱<input value={email} onChange={event => setEmail(event.target.value)} /></label><label>密码<input type="password" value={password} onChange={event => setPassword(event.target.value)} /></label>{login.error && <p className="error">{login.error.message}</p>}<button className="primary">登录</button></form></section></main>;
}

function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  return <div className="shell"><aside><Link className="logo" to="/"><span>V</span>VidInsight</Link><nav><Nav to="/" label="矩阵大盘" icon={<LayoutDashboard size={17} />}/><Nav to="/accounts" label="账号管理" icon={<Users size={17} />}/><Nav to="/videos" label="视频列表" icon={<VideoIcon size={17} />}/><Nav to="/diagnoses" label="诊断中心" icon={<Sparkles size={17} />}/><Nav to="/settings" label="数据状态" icon={<Settings2 size={17} />}/></nav><button className="logout" onClick={() => { clearToken(); navigate("/login"); }}><LogOut size={16}/>退出登录</button></aside><main className="content">{children}</main></div>;
}
function Nav({ to, label, icon }: { to: string; label: string; icon: ReactNode }) { return <Link className="nav" to={to}>{icon}{label}</Link>; }
function PeriodPicker({ period, onChange }: { period: string; onChange: (value: "day" | "week" | "month") => void }) { return <div className="period-picker">{(["day", "week", "month"] as const).map(value => <button key={value} className={period === value ? "selected" : ""} onClick={() => onChange(value)}>{value === "day" ? "日" : value === "week" ? "周" : "月"}</button>)}</div>; }
function Header({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) { return <header className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="header-actions">{children}</div></header>; }
function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="panel"><h2>{title}</h2>{children}</section>; }
function Badge({ value }: { value: string }) { const positive = ["active", "enabled", "succeeded", "complete"].some(item => value.toLowerCase().includes(item)) || value.includes("已"); return <span className={`badge ${positive ? "green" : "gray"}`}>{value}</span>; }
function Empty({ message }: { message: string }) { return <div className="empty">{message}</div>; }
function ErrorState({ message }: { message: string }) { return <div className="error">{message}</div>; }
function Loading() { return <div className="loading">正在加载数据…</div>; }

function ExportButton({ range, accountIds = [] }: { range: ReturnType<typeof dateRange>; accountIds?: string[] }) {
  const exportFile = useMutation({ mutationFn: async () => { const job = await api<{ id: string }>("/exports", { method: "POST", body: JSON.stringify({ start_at: range.start, end_at: range.end, account_ids: accountIds, period: "custom" }) }); await apiDownload(`/exports/${job.id}/download`, `vidinsight-${new Date().toISOString().slice(0, 10)}.xlsx`); } });
  return <button className="ghost" disabled={exportFile.isPending} onClick={() => exportFile.mutate()}><Download size={16}/>{exportFile.isPending ? "导出中" : "导出 Excel"}</button>;
}

function Dashboard() {
  const { period, setPeriod, range } = usePeriod();
  const overview = useQuery({ queryKey: ["overview", range], queryFn: () => api<Overview>(`/dashboard/overview?start_at=${encodeURIComponent(range.start)}&end_at=${encodeURIComponent(range.end)}`) });
  const trends = useQuery({ queryKey: ["trends", range], queryFn: () => api<Array<{ date: string; plays: number; likes: number }>>(`/dashboard/trends?start_at=${encodeURIComponent(range.start)}&end_at=${encodeURIComponent(range.end)}`) });
  const coverage = useQuery({ queryKey: ["coverage"], queryFn: () => api<{ ready_for_acceptance: boolean; metrics: Array<{ metric_code: string; coverage_rate: number }> }>("/metrics/coverage") });
  if (overview.isLoading) return <Loading />; if (overview.error || !overview.data) return <ErrorState message={(overview.error as Error).message} />;
  const m = overview.data.metrics; const cards = [["总播放", number(m.play_delta)], ["总点赞", number(m.like_delta)], ["总涨粉", number(m.follower_delta)], ["总评论", number(m.comment_delta)], ["总转发", number(m.forward_delta)], ["平均完播率", percent(m.avg_completion_rate)]];
  return <><Header title="矩阵大盘" subtitle={`${period === "day" ? "最近 1 天" : period === "week" ? "最近 7 天" : "最近 30 天"} · ${overview.data.account_count} 个账号 · ${overview.data.video_count} 条作品`}><PeriodPicker period={period} onChange={setPeriod}/><ExportButton range={range}/></Header><div className="coverage">数据验收：{coverage.data?.ready_for_acceptance ? <b className="ok">所有核心字段已就绪</b> : <b className="warn">仍有必需指标待接入</b>}</div><section className="metric-grid">{cards.map(([label, value]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>当前周期</small></article>)}</section><section className="two-col"><Panel title="表现趋势"><ResponsiveContainer width="100%" height={260}><LineChart data={trends.data || []}><CartesianGrid strokeDasharray="3 3" stroke="#e8e8e8"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line type="monotone" dataKey="plays" stroke="#18181b" strokeWidth={2}/><Line type="monotone" dataKey="likes" stroke="#71717a" strokeWidth={2}/></LineChart></ResponsiveContainer></Panel><Panel title="指标覆盖率"><ResponsiveContainer width="100%" height={260}><BarChart data={coverage.data?.metrics || []}><XAxis dataKey="metric_code" hide/><YAxis domain={[0, 1]}/><Tooltip formatter={value => percent(Number(value))}/><Bar dataKey="coverage_rate" fill="#18181b" radius={4}/></BarChart></ResponsiveContainer></Panel></section></>;
}

function Accounts() {
  const cache = useQueryClient(); const [open, setOpen] = useState(false); const [batch, setBatch] = useState(false); const [form, setForm] = useState({ nickname: "", platform_open_id: "" }); const [rows, setRows] = useState("");
  const query = useQuery({ queryKey: ["accounts"], queryFn: () => api<Account[]>("/accounts") });
  const create = useMutation({ mutationFn: () => api<Account>("/accounts", { method: "POST", body: JSON.stringify(form) }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["accounts"] }); setOpen(false); } });
  const batchCreate = useMutation({ mutationFn: () => api("/accounts/batch", { method: "POST", body: JSON.stringify(rows.split("\n").filter(Boolean).map(line => { const [nickname, platform_open_id] = line.split(",").map(item => item.trim()); return { nickname, platform_open_id }; })) }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["accounts"] }); setBatch(false); } });
  const sync = useMutation({ mutationFn: (id: string) => api(`/accounts/${id}/sync`, { method: "POST" }) });
  const toggle = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api(`/accounts/${id}/${enabled ? "disable" : "enable"}`, { method: "POST" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["accounts"] }) });
  const remove = useMutation({ mutationFn: (id: string) => api(`/accounts/${id}`, { method: "DELETE" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["accounts"] }) });
  return <><Header title="账号管理" subtitle="维护已授权的抖音矩阵账号"><button className="ghost" onClick={() => setBatch(true)}>批量录入</button><button className="primary" onClick={() => setOpen(true)}><Plus size={16}/>添加账号</button></Header>{open && <Modal title="新增账号" onClose={() => setOpen(false)}><form onSubmit={event => { event.preventDefault(); create.mutate(); }}><label>账号名称<input required value={form.nickname} onChange={event => setForm({ ...form, nickname: event.target.value })}/></label><label>抖音账号 ID<input required value={form.platform_open_id} onChange={event => setForm({ ...form, platform_open_id: event.target.value })}/></label><button className="primary">保存</button></form></Modal>}{batch && <Modal title="批量录入账号" onClose={() => setBatch(false)}><form onSubmit={event => { event.preventDefault(); batchCreate.mutate(); }}><label>每行：账号名称,抖音账号 ID<textarea required rows={7} placeholder="品牌主号,open_id_001\n知识栏目,open_id_002" value={rows} onChange={event => setRows(event.target.value)}/></label>{batchCreate.error && <p className="error">{batchCreate.error.message}</p>}<button className="primary">提交导入</button></form></Modal>}<Panel title="账号列表"><table><thead><tr><th>账号</th><th>账号 ID</th><th>授权状态</th><th>采集</th><th>最后同步</th><th/></tr></thead><tbody>{query.data?.map(account => <tr key={account.id}><td><Link className="row-link" to={`/accounts/${account.id}`}>{account.nickname}</Link></td><td className="muted">{account.platform_open_id}</td><td><Badge value={account.authorization_status}/></td><td><Badge value={account.collection_enabled ? "enabled" : "disabled"}/></td><td>{account.last_synced_at ? new Date(account.last_synced_at).toLocaleString() : "—"}</td><td className="actions"><button title="手动刷新" onClick={() => sync.mutate(account.id)}><RefreshCw size={16}/></button><button onClick={() => toggle.mutate({ id: account.id, enabled: account.collection_enabled })}>{account.collection_enabled ? "停用" : "启用"}</button><button title="删除账号" onClick={() => window.confirm(`确认删除 ${account.nickname} 及其历史数据？`) && remove.mutate(account.id)}><Trash2 size={16}/></button></td></tr>)}</tbody></table>{query.data?.length === 0 && <Empty message="还没有账号，先添加或批量录入账号。"/>}</Panel></>;
}

function AccountDetail() {
  const { accountId = "" } = useParams(); const { period, setPeriod, range } = usePeriod();
  const query = useQuery({ queryKey: ["account", accountId, range], queryFn: () => api<{ account: Account; metrics: Overview["metrics"]; trends: Array<{ date: string; plays: number; likes: number }>; videos: Video[] }>(`/accounts/${accountId}/analytics?start_at=${encodeURIComponent(range.start)}&end_at=${encodeURIComponent(range.end)}`) });
  if (query.isLoading) return <Loading />; if (query.error || !query.data) return <ErrorState message={(query.error as Error).message} />;
  return <><Header title={query.data.account.nickname} subtitle={`账号 ID：${query.data.account.platform_open_id}`}><PeriodPicker period={period} onChange={setPeriod}/><ExportButton range={range} accountIds={[accountId]}/></Header><section className="two-col"><Panel title="数据趋势"><ResponsiveContainer width="100%" height={260}><LineChart data={query.data.trends}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line dataKey="plays" stroke="#18181b"/><Line dataKey="likes" stroke="#71717a"/></LineChart></ResponsiveContainer></Panel><Panel title="周期汇总"><div className="summary-list"><span>播放 <b>{number(query.data.metrics.play_delta)}</b></span><span>点赞 <b>{number(query.data.metrics.like_delta)}</b></span><span>涨粉 <b>{number(query.data.metrics.follower_delta)}</b></span><span>平均完播 <b>{percent(query.data.metrics.avg_completion_rate)}</b></span></div></Panel></section><Panel title="作品与诊断"><VideoTable videos={query.data.videos}/></Panel></>;
}

function VideoTable({ videos }: { videos: Video[] }) { return <table><thead><tr><th>作品</th><th>播放</th><th>点赞</th><th>评论</th><th>转发</th><th>完播率</th><th/></tr></thead><tbody>{videos.map(video => <tr key={video.id}><td><Link className="row-link" to={`/videos/${video.id}`}>{video.title}</Link><small>{new Date(video.published_at).toLocaleString()}</small></td><td>{number(video.latest_metrics.play_count)}</td><td>{number(video.latest_metrics.like_count)}</td><td>{number(video.latest_metrics.comment_count)}</td><td>{number(video.latest_metrics.forward_count)}</td><td>{percent(video.latest_metrics.completion_rate)}</td><td><Link className="text-button" to={`/videos/${video.id}`}>详情</Link></td></tr>)}</tbody></table>; }

function Videos() {
  const [search, setSearch] = useState(""); const [sort, setSort] = useState("-published_at"); const query = useQuery({ queryKey: ["videos", search, sort], queryFn: () => api<Video[]>(`/videos?sort=${sort}${search ? `&q=${encodeURIComponent(search)}` : ""}`) });
  return <><Header title="视频列表" subtitle="按标题搜索并按关键指标排序"><select value={sort} onChange={event => setSort(event.target.value)}><option value="-published_at">最新发布</option><option value="-play_count">播放量从高到低</option><option value="-like_count">点赞从高到低</option><option value="-comment_count">评论从高到低</option></select></Header><div className="filter"><input placeholder="搜索视频标题" value={search} onChange={event => setSearch(event.target.value)}/></div><Panel title="作品明细">{query.data?.length ? <VideoTable videos={query.data}/> : <Empty message="暂无视频数据，请先同步或导入。"/>}</Panel></>;
}

function VideoDetail() {
  const { videoId = "" } = useParams(); const cache = useQueryClient(); const query = useQuery({ queryKey: ["video", videoId], queryFn: () => api<Video>(`/videos/${videoId}`) }); const diagnose = useMutation({ mutationFn: () => api(`/videos/${videoId}/diagnose`, { method: "POST" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["diagnoses"] }) });
  if (query.isLoading) return <Loading />; if (query.error || !query.data) return <ErrorState message={(query.error as Error).message} />; const m = query.data.latest_metrics;
  return <><Header title={query.data.title} subtitle={`作品 ID：${query.data.platform_item_id}`}><button className="primary" disabled={diagnose.isPending} onClick={() => diagnose.mutate()}><Sparkles size={16}/>{diagnose.isPending ? "诊断中" : "生成诊断"}</button></Header>{diagnose.error && <ErrorState message={diagnose.error.message}/>}<section className="metric-grid">{[["播放", number(m.play_count)], ["点赞", number(m.like_count)], ["评论", number(m.comment_count)], ["转发", number(m.forward_count)], ["完播率", percent(m.completion_rate)], ["涨粉转化", percent(m.video_follow_conversion)]].map(([label, value]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong></article>)}</section><Panel title="指标历史"><ResponsiveContainer width="100%" height={280}><LineChart data={query.data.history || []}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="collected_at" hide/><YAxis/><Tooltip/><Line dataKey="play_count" stroke="#18181b"/><Line dataKey="like_count" stroke="#71717a"/></LineChart></ResponsiveContainer></Panel></>;
}

function Diagnoses() { const query = useQuery({ queryKey: ["diagnoses"], queryFn: () => api<Array<{ id: string; title: string; suggestion: string; rule_code: string; evidence: Record<string, unknown> }>>("/diagnoses") }); return <><Header title="诊断中心" subtitle="数据驱动的运营参考建议"/>{query.data?.length ? <section className="diagnosis-grid">{query.data.map(item => <article className="diagnosis" key={item.id}><Badge value={item.rule_code}/><h3>{item.title}</h3><p>{item.suggestion}</p><pre>{JSON.stringify(item.evidence, null, 2)}</pre><small>基于相关性数据，仅供运营参考。</small></article>)}</section> : <Empty message="暂无诊断结果。进入视频详情后可生成诊断。"/>}</>; }
function Settings() { const coverage = useQuery({ queryKey: ["coverage"], queryFn: () => api<{ ready_for_acceptance: boolean; metrics: Array<{ metric_code: string; scope: string; covered: number; total: number; coverage_rate: number }> }>("/metrics/coverage") }); return <><Header title="数据状态" subtitle="必需指标覆盖与上线门槛"/><Panel title={coverage.data?.ready_for_acceptance ? "已满足验收" : "尚未满足验收"}><table><thead><tr><th>指标</th><th>粒度</th><th>覆盖</th><th>状态</th></tr></thead><tbody>{coverage.data?.metrics.map(item => <tr key={item.metric_code}><td>{item.metric_code}</td><td>{item.scope}</td><td>{item.covered}/{item.total}</td><td><Badge value={item.coverage_rate === 1 && item.total > 0 ? "complete" : "pending"}/></td></tr>)}</tbody></table></Panel></>; }
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) { return <div className="modal-backdrop"><section className="modal"><button className="close" onClick={onClose}>×</button><h2>{title}</h2>{children}</section></div>; }
function App() { return <Routes><Route path="/login" element={token() ? <Navigate to="/"/> : <Login/>}/><Route path="/*" element={token() ? <Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/accounts" element={<Accounts/>}/><Route path="/accounts/:accountId" element={<AccountDetail/>}/><Route path="/videos" element={<Videos/>}/><Route path="/videos/:videoId" element={<VideoDetail/>}/><Route path="/diagnoses" element={<Diagnoses/>}/><Route path="/settings" element={<Settings/>}/></Routes></Layout> : <Navigate to="/login"/>}/></Routes>; }
createRoot(document.getElementById("root")!).render(<BrowserRouter><QueryClientProvider client={client}><App/></QueryClientProvider></BrowserRouter>);
