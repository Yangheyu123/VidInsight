import { FormEvent, ReactNode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { BarChart3, Download, LayoutDashboard, LogOut, Plus, RefreshCw, Settings2, Sparkles, Trash2, Users, Video as VideoIcon } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Account, api, clearToken, dateRange, Overview, setToken, token, Video } from "./api";
import "./styles.css";

const client = new QueryClient();
const range = dateRange();

function number(value: number | null | undefined): string { return value == null ? "—" : new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 }).format(value); }
function percent(value: number | null | undefined): string { return value == null ? "—" : `${(value * 100).toFixed(1)}%`; }

function Login(): JSX.Element {
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@vidinsight.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const mutation = useMutation({ mutationFn: () => api<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }), onSuccess: (value) => { setToken(value.access_token); navigate("/"); } });
  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate(); };
  return <main className="login"><section className="login-card"><div className="brand-mark">V</div><h1>VidInsight</h1><p>内部短视频数据看台</p><form onSubmit={submit}><label>邮箱<input value={email} onChange={e => setEmail(e.target.value)} /></label><label>密码<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>{mutation.error && <p className="error">{mutation.error.message}</p>}<button className="primary" type="submit">登录</button></form></section></main>;
}

function Layout({ children }: { children: ReactNode }): JSX.Element {
  const navigate = useNavigate();
  return <div className="shell"><aside><Link className="logo" to="/"><span>V</span> VidInsight</Link><nav><Nav to="/" icon={<LayoutDashboard size={17} />} label="矩阵大盘"/><Nav to="/accounts" icon={<Users size={17} />} label="账号管理"/><Nav to="/videos" icon={<VideoIcon size={17} />} label="视频列表"/><Nav to="/diagnoses" icon={<Sparkles size={17} />} label="诊断中心"/><Nav to="/settings" icon={<Settings2 size={17} />} label="数据状态"/></nav><button className="logout" onClick={() => { clearToken(); navigate("/login"); }}><LogOut size={16} />退出登录</button></aside><main className="content">{children}</main></div>;
}
function Nav({ to, icon, label }: { to: string; icon: ReactNode; label: string }): JSX.Element { return <Link className="nav" to={to}>{icon}{label}</Link>; }

function Dashboard(): JSX.Element {
  const { data, isLoading, error } = useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>(`/dashboard/overview?start_at=${encodeURIComponent(range.start)}&end_at=${encodeURIComponent(range.end)}`) });
  const trend = useQuery({ queryKey: ["trends"], queryFn: () => api<Array<{ date: string; plays: number; likes: number; comments: number; forwards: number }>>(`/dashboard/trends?start_at=${encodeURIComponent(range.start)}&end_at=${encodeURIComponent(range.end)}`) });
  const coverage = useQuery({ queryKey: ["coverage"], queryFn: () => api<{ ready_for_acceptance: boolean; metrics: Array<{ metric_code: string; coverage_rate: number }> }>("/metrics/coverage") });
  if (isLoading) return <Loading />;
  if (error || !data) return <ErrorState message={(error as Error).message} />;
  const metrics = data.metrics;
  const cards = [["总播放", number(metrics.play_delta)], ["总点赞", number(metrics.like_delta)], ["总涨粉", number(metrics.follower_delta)], ["总评论", number(metrics.comment_delta)], ["总转发", number(metrics.forward_delta)], ["平均完播率", percent(metrics.avg_completion_rate)]];
  return <><Header title="矩阵大盘" subtitle={`最近 7 天 · ${data.account_count} 个账号 · ${data.video_count} 条作品`} /><div className="coverage">数据验收：{coverage.data?.ready_for_acceptance ? <b className="ok">全部核心字段就绪</b> : <b className="warn">仍有必需指标待接入</b>}</div><section className="metric-grid">{cards.map(([label, value]) => <article className="metric" key={label}><span>{label}</span><strong>{value}</strong><small>本周期</small></article>)}</section><section className="two-col"><Panel title="表现趋势"><ResponsiveContainer width="100%" height={260}><LineChart data={trend.data || []}><CartesianGrid strokeDasharray="3 3" stroke="#e8e8e8"/><XAxis dataKey="date"/><YAxis/><Tooltip/><Line type="monotone" dataKey="plays" stroke="#18181b" strokeWidth={2}/><Line type="monotone" dataKey="likes" stroke="#71717a" strokeWidth={2}/></LineChart></ResponsiveContainer></Panel><Panel title="指标覆盖率"><ResponsiveContainer width="100%" height={260}><BarChart data={coverage.data?.metrics || []}><XAxis dataKey="metric_code" hide/><YAxis domain={[0, 1]}/><Tooltip formatter={(value) => percent(Number(value))}/><Bar dataKey="coverage_rate" fill="#18181b" radius={4}/></BarChart></ResponsiveContainer></Panel></section></>;
}

function Accounts(): JSX.Element {
  const cache = useQueryClient(); const [open, setOpen] = useState(false); const [form, setForm] = useState({ nickname: "", platform_open_id: "" });
  const query = useQuery({ queryKey: ["accounts"], queryFn: () => api<Account[]>("/accounts") });
  const create = useMutation({ mutationFn: () => api<Account>("/accounts", { method: "POST", body: JSON.stringify(form) }), onSuccess: () => { cache.invalidateQueries({ queryKey: ["accounts"] }); setOpen(false); } });
  const sync = useMutation({ mutationFn: (id: string) => api(`/accounts/${id}/sync`, { method: "POST" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["accounts"] }) });
  const toggle = useMutation({ mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => api(`/accounts/${id}/${enabled ? "disable" : "enable"}`, { method: "POST" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["accounts"] }) });
  const remove = useMutation({ mutationFn: (id: string) => api(`/accounts/${id}`, { method: "DELETE" }), onSuccess: () => cache.invalidateQueries({ queryKey: ["accounts"] }) });
  return <><Header title="账号管理" subtitle="维护已授权的抖音矩阵账号" action={<button className="primary" onClick={() => setOpen(true)}><Plus size={16}/>添加账号</button>}/>{open && <Modal title="新增账号" onClose={() => setOpen(false)}><form onSubmit={e => { e.preventDefault(); create.mutate(); }}><label>账号名称<input value={form.nickname} onChange={e => setForm({ ...form, nickname: e.target.value })}/></label><label>抖音账号 ID<input value={form.platform_open_id} onChange={e => setForm({ ...form, platform_open_id: e.target.value })}/></label><button className="primary">保存</button></form></Modal>}<Panel title="账号列表"><table><thead><tr><th>账号</th><th>账号 ID</th><th>授权状态</th><th>采集</th><th>最后同步</th><th></th></tr></thead><tbody>{query.data?.map(account => <tr key={account.id}><td><b>{account.nickname}</b></td><td className="muted">{account.platform_open_id}</td><td><Badge value={account.authorization_status}/></td><td><Badge value={account.collection_enabled ? "已启用" : "已停用"}/></td><td>{account.last_synced_at ? new Date(account.last_synced_at).toLocaleString() : "—"}</td><td className="actions"><button onClick={() => sync.mutate(account.id)} title="手动刷新"><RefreshCw size={16}/></button><button onClick={() => toggle.mutate({ id: account.id, enabled: account.collection_enabled })}>{account.collection_enabled ? "停用" : "启用"}</button></td></tr>)}</tbody></table>{query.data?.length === 0 && <Empty message="还没有账号，先添加一个抖音账号。"/>}</Panel></>;
}

function Videos(): JSX.Element {
  const [search, setSearch] = useState(""); const query = useQuery({ queryKey: ["videos", search], queryFn: () => api<Video[]>(`/videos${search ? `?q=${encodeURIComponent(search)}` : ""}`) });
  return <><Header title="视频列表" subtitle="按账号、时间和指标筛选排序"/><div className="filter"><input placeholder="搜索视频标题" value={search} onChange={e => setSearch(e.target.value)}/></div><Panel title="作品明细"><table><thead><tr><th>作品</th><th>播放</th><th>点赞</th><th>评论</th><th>转发</th><th>完播率</th></tr></thead><tbody>{query.data?.map(video => <tr key={video.id}><td><b>{video.title}</b><small>{new Date(video.published_at).toLocaleString()}</small></td><td>{number(video.latest_metrics.play_count)}</td><td>{number(video.latest_metrics.like_count)}</td><td>{number(video.latest_metrics.comment_count)}</td><td>{number(video.latest_metrics.forward_count)}</td><td>{percent(video.latest_metrics.completion_rate)}</td></tr>)}</tbody></table>{query.data?.length === 0 && <Empty message="暂无视频数据，请先导入或同步。"/>}</Panel></>;
}

function Diagnoses(): JSX.Element {
  const query = useQuery({ queryKey: ["diagnoses"], queryFn: () => api<Array<{ id: string; rule_code: string; title: string; suggestion: string; evidence: Record<string, unknown> }>>("/diagnoses") });
  return <><Header title="诊断中心" subtitle="基于数据的运营参考建议"/><section className="diagnosis-grid">{query.data?.map(item => <article className="diagnosis" key={item.id}><Badge value={item.rule_code}/><h3>{item.title}</h3><p>{item.suggestion}</p><pre>{JSON.stringify(item.evidence, null, 2)}</pre><small>基于相关性数据，仅供运营参考。</small></article>)}</section>{query.data?.length === 0 && <Empty message="暂无诊断结果。导入完整指标后，可在视频详情中触发重新诊断。"/>}</>;
}

function Settings(): JSX.Element {
  const coverage = useQuery({ queryKey: ["coverage"], queryFn: () => api<{ ready_for_acceptance: boolean; metrics: Array<{ metric_code: string; scope: string; covered: number; total: number; coverage_rate: number }> }>("/metrics/coverage") });
  return <><Header title="数据状态" subtitle="必需指标覆盖与上线门槛"/><Panel title={coverage.data?.ready_for_acceptance ? "已满足验收" : "尚未满足验收"}><table><thead><tr><th>指标</th><th>粒度</th><th>覆盖</th><th>状态</th></tr></thead><tbody>{coverage.data?.metrics.map(item => <tr key={item.metric_code}><td>{item.metric_code}</td><td>{item.scope}</td><td>{item.covered}/{item.total}</td><td><Badge value={item.coverage_rate === 1 && item.total > 0 ? "已覆盖" : "待接入"}/></td></tr>)}</tbody></table></Panel></>;
}

function Header({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }): JSX.Element { return <header className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="header-actions">{action}<button className="ghost"><Download size={16}/>导出</button></div></header>; }
function Panel({ title, children }: { title: string; children: ReactNode }): JSX.Element { return <section className="panel"><h2>{title}</h2>{children}</section>; }
function Badge({ value }: { value: string }): JSX.Element { return <span className={`badge ${value.includes("已") || value === "active" ? "green" : "gray"}`}>{value}</span>; }
function Empty({ message }: { message: string }): JSX.Element { return <div className="empty">{message}</div>; }
function Loading(): JSX.Element { return <div className="loading">正在加载数据…</div>; }
function ErrorState({ message }: { message: string }): JSX.Element { return <div className="error">加载失败：{message}</div>; }
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }): JSX.Element { return <div className="modal-backdrop"><section className="modal"><button className="close" onClick={onClose}>×</button><h2>{title}</h2>{children}</section></div>; }

function App(): JSX.Element { return <Routes><Route path="/login" element={token() ? <Navigate to="/"/> : <Login/>}/><Route path="/*" element={token() ? <Layout><Routes><Route path="/" element={<Dashboard/>}/><Route path="/accounts" element={<Accounts/>}/><Route path="/videos" element={<Videos/>}/><Route path="/diagnoses" element={<Diagnoses/>}/><Route path="/settings" element={<Settings/>}/></Routes></Layout> : <Navigate to="/login"/>}/></Routes>; }

createRoot(document.getElementById("root")!).render(<BrowserRouter><QueryClientProvider client={client}><App/></QueryClientProvider></BrowserRouter>);
