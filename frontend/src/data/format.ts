/* ============================================================
   展示层格式化:数字走中文单位,标签走 Geist Mono
   ============================================================ */

/** 播放/曝光等大数:中文单位(万/亿),一位小数 */
export function fmtNum(n: number | null | undefined): string {
  if (n == null) return '—'
  if (n >= 1_0000_0000) return `${(n / 1_0000_0000).toFixed(1)}亿`
  if (n >= 1_0000) return `${(n / 1_0000).toFixed(1)}万`
  return n.toLocaleString('zh-CN')
}

/** 比率 0-1 → 百分比,一位小数 */
export function fmtPct(r: number | null | undefined, digits = 1): string {
  if (r == null) return '—'
  return `${(r * 100).toFixed(digits)}%`
}

/** 秒 → m:ss */
export function fmtDur(sec: number | null | undefined): string {
  if (sec == null) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

/** 环比差值 → "+12.4%" / "-3.1%" */
export function fmtDelta(r: number | null | undefined): string {
  if (r == null) return '—'
  const sign = r >= 0 ? '+' : ''
  return `${sign}${(r * 100).toFixed(1)}%`
}

/** ISO → "MM-DD" 或 "MM-DD HH:mm" */
export function fmtDate(iso: string, withTime = false): string {
  const d = new Date(iso)
  const md = `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  if (!withTime) return md
  const hm = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return `${md} ${hm}`
}
