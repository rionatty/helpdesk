// Lays a week of tasks out as bars, the way calendars draw multi-day events:
// a task that runs over several days is one bar across them, not a copy in
// every cell. Bars stack into lanes, so ones that overlap never collide.

export interface CalItem {
  name: string;
  subject?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  start_time?: string | null;
  [key: string]: any;
}

export interface Segment {
  item: CalItem;
  /** First column of the bar in this week, 0 = Monday. */
  start: number;
  /** Days the bar covers in this week. */
  span: number;
  /** Row inside the week, 0 = top. */
  lane: number;
  /** The task started in an earlier week / runs on into a later one. */
  continuesBefore: boolean;
  continuesAfter: boolean;
}

const DAY_MS = 86400000;

/** "YYYY-MM-DD" as whole days since the epoch - immune to time zones and
 * daylight saving, which a Date diff is not. */
export function dayNumber(iso: string): number {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / DAY_MS);
}

/** The first and last day a task covers. Only one date means that day;
 * dates entered backwards are put the right way round. */
export function itemDays(item: CalItem): [number, number] | null {
  const first = item.start_date || item.end_date;
  const last = item.end_date || item.start_date;
  if (!first || !last) return null;
  const a = dayNumber(first);
  const b = dayNumber(last);
  return a <= b ? [a, b] : [b, a];
}

/** Bars for the week starting on `weekStartIso` (a Monday), with lanes
 * assigned. Earlier bars take the higher lanes, and among bars starting the
 * same day the longer one goes first, so long bars keep a steady lane. */
export function layoutWeek(
  items: CalItem[],
  weekStartIso: string
): { segments: Segment[]; laneCount: number } {
  const first = dayNumber(weekStartIso);
  const last = first + 6;
  const pending: Omit<Segment, "lane">[] = [];
  for (const item of items) {
    const days = itemDays(item);
    if (!days) continue;
    const [a, b] = days;
    if (b < first || a > last) continue;
    const s = Math.max(a, first);
    const e = Math.min(b, last);
    pending.push({
      item,
      start: s - first,
      span: e - s + 1,
      continuesBefore: a < first,
      continuesAfter: b > last,
    });
  }
  pending.sort(
    (x, y) =>
      x.start - y.start ||
      y.span - x.span ||
      (x.item.start_time || "").localeCompare(y.item.start_time || "") ||
      (x.item.subject || "").localeCompare(y.item.subject || "")
  );

  const lanes: [number, number][][] = [];
  const segments: Segment[] = [];
  for (const seg of pending) {
    const end = seg.start + seg.span - 1;
    let lane = 0;
    while (lanes[lane]?.some(([a, b]) => seg.start <= b && a <= end)) lane++;
    (lanes[lane] ||= []).push([seg.start, end]);
    segments.push({ ...seg, lane });
  }
  return { segments, laneCount: lanes.length };
}

/** How many bars each day of the week loses when only `maxLanes` lanes
 * are shown - the "+N more" under each day. */
export function hiddenPerDay(segments: Segment[], maxLanes: number): number[] {
  const hidden = [0, 0, 0, 0, 0, 0, 0];
  for (const seg of segments) {
    if (seg.lane < maxLanes) continue;
    for (let d = seg.start; d < seg.start + seg.span; d++) hidden[d]++;
  }
  return hidden;
}
