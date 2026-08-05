export type Account = { id: string; platform_open_id: string; nickname: string; alias?: string | null; authorization_status: string; collection_enabled: boolean; priority: number; last_synced_at?: string | null };
export type Metric = { play_count: number; like_count: number; comment_count: number; share_count: number; forward_count: number; completion_rate: number | null; video_follow_conversion?: number | null };
export type Video = { id: string; account_id: string; platform_item_id: string; title: string; published_at: string; latest_metrics: Metric; history?: Array<Metric & { collected_at: string; source: string }>; diagnoses?: Array<{ rule_code: string; title: string; suggestion: string }> };
export type Overview = { metrics: { play_delta: number; like_delta: number; comment_delta: number; forward_delta: number; follower_delta: number; avg_completion_rate: number | null }; account_count: number; video_count: number };

const base = "/api/v1";

export function token(): string | null { return localStorage.getItem("vidinsight_token"); }
export function setToken(value: string): void { localStorage.setItem("vidinsight_token", value); }
export function clearToken(): void { localStorage.removeItem("vidinsight_token"); }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  const response = await fetch(`${base}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(body.detail || "请求失败");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const response = await fetch(`${base}${path}`, { headers: { Authorization: `Bearer ${token()}` } });
  if (!response.ok) throw new Error("导出文件下载失败");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); URL.revokeObjectURL(url);
}

export const dateRange = (): { start: string; end: string } => {
  const end = new Date();
  const start = new Date(end); start.setDate(end.getDate() - 7);
  return { start: start.toISOString(), end: end.toISOString() };
};
