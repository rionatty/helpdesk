<template>
  <!-- The project plan on a calendar: milestones (diamond at the due date,
       light bar over their tasks' span) with their tasks as bars coloured by
       status. Read-only. Customers see it too, with the API's customer
       scoping (no internal tasks, only customer-visible milestones). -->
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <div class="size-7 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
        <LucideCalendarRange class="size-4" />
      </div>
      <span class="text-base font-semibold text-ink-gray-8">{{ __("Timeline") }}</span>
      <span v-if="total" class="text-xs text-ink-gray-5">
        {{ __("{0} of {1} tasks scheduled", [total - unscheduled, total]) }}
      </span>
      <span class="flex-1" />
      <div class="inline-flex rounded-md bg-surface-gray-2 p-0.5">
        <button
          v-for="z in ZOOMS"
          :key="z.key"
          type="button"
          class="rounded px-2.5 py-1 text-xs"
          :class="zoom === z.key ? 'bg-surface-white text-ink-gray-9 shadow-sm' : 'text-ink-gray-6'"
          @click="zoom = z.key"
        >
          {{ z.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="h-24 rounded-lg bg-surface-gray-2 animate-pulse" />
    <p v-else-if="!rows.length" class="rounded-lg bg-surface-gray-1 p-4 text-sm text-ink-gray-6">
      {{ __("Give tasks start and end dates, or milestones a due date, to see the plan here.") }}
    </p>
    <div v-else class="overflow-x-auto rounded-lg ring-1 ring-outline-gray-2">
      <div class="relative" :style="{ width: LABEL + chartWidth + 'px' }">
        <!-- Date scale -->
        <div class="flex border-b border-outline-gray-2 bg-surface-gray-1">
          <div
            class="sticky left-0 z-20 shrink-0 border-e border-outline-gray-2 bg-surface-gray-1"
            :style="{ width: LABEL + 'px' }"
          />
          <div class="relative h-7 shrink-0" :style="{ width: chartWidth + 'px' }">
            <span
              v-for="t in ticks"
              :key="t.x"
              class="absolute top-0 h-full whitespace-nowrap border-s border-outline-gray-2 ps-1 pt-1.5 text-[10px] text-ink-gray-5"
              :style="{ left: t.x + 'px' }"
            >
              {{ t.label }}
            </span>
          </div>
        </div>

        <!-- Rows -->
        <div
          v-for="r in rows"
          :key="r.key"
          class="flex h-8 items-center border-b border-outline-gray-1 last:border-b-0"
        >
          <div
            class="sticky left-0 z-10 flex h-full shrink-0 items-center gap-1.5 overflow-hidden border-e border-outline-gray-2 bg-surface-white px-2 text-xs"
            :style="{ width: LABEL + 'px' }"
            :title="r.label"
          >
            <template v-if="r.kind === 'task'">
              <span
                class="truncate ps-3"
                :class="r.status === 'Done' ? 'text-ink-gray-4 line-through' : 'text-ink-gray-7'"
              >
                {{ r.label }}
              </span>
              <span
                v-if="r.client"
                class="shrink-0 rounded bg-amber-100 px-1 text-[9px] font-semibold uppercase text-amber-700"
              >
                {{ r.client }}
              </span>
            </template>
            <template v-else>
              <button
                v-if="r.collapsible"
                type="button"
                class="shrink-0 rounded p-0.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
                :aria-expanded="!r.collapsed"
                :title="r.collapsed ? __('Show tasks') : __('Hide tasks')"
                @click="toggle(r.name)"
              >
                <LucideChevronRight
                  class="size-3.5 transition-transform"
                  :class="r.collapsed ? '' : 'rotate-90'"
                />
              </button>
              <span
                v-if="r.color"
                class="size-2 shrink-0 rounded-full"
                :style="{ background: r.color }"
              />
              <span class="truncate font-semibold text-ink-gray-8">{{ r.label }}</span>
              <span
                v-if="r.hidden"
                class="shrink-0 rounded bg-surface-gray-2 px-1 text-[10px] text-ink-gray-6"
                :title="__('{0} tasks hidden', [r.hidden])"
              >
                {{ r.hidden }}
              </span>
            </template>
          </div>
          <div class="relative h-full shrink-0" :style="{ width: chartWidth + 'px' }">
            <template v-if="r.kind === 'milestone'">
              <div
                v-if="r.spanX !== null"
                class="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full opacity-40"
                :style="{ left: r.spanX + 'px', width: r.spanW + 'px', background: r.color }"
              />
              <div
                v-if="r.dueX !== null"
                class="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rotate-45 ring-2 ring-surface-white"
                :style="{ left: r.dueX + 'px', background: r.done ? '#10b981' : r.color }"
                :title="r.tip"
              />
            </template>
            <div
              v-else-if="r.kind === 'task'"
              class="absolute top-2 bottom-2 rounded"
              :class="[r.bar, r.overdue ? 'ring-2 ring-red-500' : '']"
              :style="{ left: r.x + 'px', width: r.w + 'px' }"
              :title="r.tip"
            />
          </div>
        </div>

        <!-- Today -->
        <div
          v-if="todayX !== null"
          class="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-red-500 opacity-70"
          :style="{ left: LABEL + todayX + 'px' }"
        />
      </div>
    </div>

    <div
      v-if="rows.length"
      class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-gray-5"
    >
      <span v-for="s in LEGEND" :key="s.label" class="inline-flex items-center gap-1">
        <span class="size-2.5 rounded-sm" :class="s.cls" />{{ s.label }}
      </span>
      <span class="inline-flex items-center gap-1">
        <span class="size-2.5 rounded-sm ring-2 ring-red-500" />{{ __("Overdue") }}
      </span>
      <span class="inline-flex items-center gap-1">
        <span class="h-2.5 w-0.5 bg-red-500 opacity-70" />{{ __("Today") }}
      </span>
      <span v-if="unscheduled" class="ms-auto">
        {{ __("{0} tasks without dates are not shown", [unscheduled]) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { createResource, dayjs } from "frappe-ui";
import { __ } from "@/translation";
import { buildMilestoneColors, milestoneColorOf } from "@/utils";
import LucideCalendarRange from "~icons/lucide/calendar-range";
import LucideChevronRight from "~icons/lucide/chevron-right";
import {
  NO_MILESTONE,
  useMilestoneCollapse,
} from "@/composables/useMilestoneCollapse";

const props = defineProps<{
  projectId: string;
  editable?: boolean;
  projectStart?: string | null;
  projectEnd?: string | null;
}>();

// A milestone folded in the list above is folded here too: its task bars
// drop out and the row keeps a count of what it is hiding.
const { isCollapsed, toggle } = useMilestoneCollapse(() => props.projectId);

const LABEL = 220; // px for the name column
const ZOOMS = [
  { key: "week", label: __("Weeks"), px: 20 },
  { key: "month", label: __("Months"), px: 6 },
];
const zoom = ref("week");
const px = computed(() => ZOOMS.find((z) => z.key === zoom.value)?.px || 20);

const STATUS_BAR: Record<string, string> = {
  "To Do": "bg-gray-300",
  "In Progress": "bg-blue-400",
  Pending: "bg-amber-400",
  Postponed: "bg-violet-400",
  Done: "bg-green-500",
};
const LEGEND = Object.entries(STATUS_BAR).map(([label, cls]) => ({ label: __(label), cls }));

const tasks = createResource({
  url: "helpdesk.api.addon.get_tasks",
  makeParams: () => ({ project: props.projectId }),
  auto: true,
});
const milestones = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: props.projectId }),
  auto: true,
});
function reload() {
  tasks.reload();
  milestones.reload();
}
defineExpose({ reload });

const loading = computed(
  () => (tasks.loading && !tasks.data) || (milestones.loading && !milestones.data)
);

const today = dayjs().startOf("day");
const day = (s: any) => (s ? dayjs(s).startOf("day") : null);

const colors = computed(() =>
  buildMilestoneColors((milestones.data || []).map((m: any) => m.name))
);

// A task with only one date is drawn as a one-day bar on that date.
const items = computed(() =>
  (tasks.data || []).map((t: any) => {
    const s = day(t.start_date) || day(t.end_date);
    const e = day(t.end_date) || day(t.start_date);
    return { ...t, s, e };
  })
);

const range = computed(() => {
  const dates: any[] = [];
  for (const t of items.value) if (t.s) dates.push(t.s, t.e);
  for (const m of milestones.data || []) {
    const due = day(m.due_date);
    if (due) dates.push(due);
  }
  const ps = day(props.projectStart);
  const pe = day(props.projectEnd);
  if (ps) dates.push(ps);
  if (pe) dates.push(pe);
  if (!dates.length) return null;
  let min = dates.reduce((a, b) => (b.isBefore(a) ? b : a));
  let max = dates.reduce((a, b) => (b.isAfter(a) ? b : a));
  // Keep today in view when it is reasonably near the plan.
  if (today.isAfter(min.subtract(30, "day")) && today.isBefore(max.add(30, "day"))) {
    if (today.isBefore(min)) min = today;
    if (today.isAfter(max)) max = today;
  }
  return { start: min.subtract(3, "day"), end: max.add(7, "day") };
});

const chartWidth = computed(() =>
  range.value ? (range.value.end.diff(range.value.start, "day") + 1) * px.value : 0
);
const xOf = (d: any) => d.diff(range.value!.start, "day") * px.value;

const ticks = computed(() => {
  if (!range.value) return [];
  const out: { x: number; label: string }[] = [];
  const { start, end } = range.value;
  if (zoom.value === "week") {
    let d = start.day(1); // Monday
    if (d.isBefore(start)) d = d.add(7, "day");
    while (!d.isAfter(end)) {
      out.push({ x: xOf(d), label: d.format("D MMM") });
      d = d.add(7, "day");
    }
  } else {
    let d = start.startOf("month");
    if (d.isBefore(start)) d = d.add(1, "month");
    while (!d.isAfter(end)) {
      out.push({ x: xOf(d), label: d.format("MMM YYYY") });
      d = d.add(1, "month");
    }
  }
  return out;
});

const todayX = computed(() =>
  range.value && !today.isBefore(range.value.start) && !today.isAfter(range.value.end)
    ? xOf(today) + px.value / 2
    : null
);

function sortTasks(list: any[]) {
  return list.sort((a, b) => a.s.diff(b.s) || a.e.diff(b.e));
}

const rows = computed(() => {
  if (!range.value) return [];
  const out: any[] = [];
  const taskRow = (t: any) => ({
    key: "t:" + t.name,
    kind: "task",
    label: t.subject,
    status: t.status,
    bar: STATUS_BAR[t.status] || "bg-gray-300",
    x: xOf(t.s),
    w: Math.max(px.value, xOf(t.e.add(1, "day")) - xOf(t.s)),
    overdue: t.status !== "Done" && t.e.isBefore(today),
    // Who does the work is internal: agents only.
    client:
      props.editable && (t.responsibility === "Client" || t.responsibility === "Joint")
        ? __(t.responsibility)
        : null,
    tip: [
      t.subject,
      t.s.format("D MMM") + " - " + t.e.format("D MMM YYYY"),
      __(t.status),
      t.assigned_to_name,
    ]
      .filter(Boolean)
      .join(" · "),
  });

  const scheduled = items.value.filter((t: any) => t.s);
  const byMilestone: Record<string, any[]> = {};
  for (const t of scheduled) {
    const k = t.milestone || "";
    (byMilestone[k] = byMilestone[k] || []).push(t);
  }
  const known = new Set((milestones.data || []).map((m: any) => m.name));

  for (const m of milestones.data || []) {
    const list = sortTasks(byMilestone[m.name] || []);
    const due = day(m.due_date);
    if (!list.length && !due) continue;
    let spanStart: any = null;
    let spanEnd: any = null;
    if (list.length) {
      spanStart = list[0].s;
      spanEnd = list.reduce((a: any, t: any) => (t.e.isAfter(a) ? t.e : a), list[0].e);
    }
    if (due && (!spanEnd || due.isAfter(spanEnd))) spanEnd = due;
    const folded = isCollapsed(m.name);
    out.push({
      key: "m:" + m.name,
      kind: "milestone",
      name: m.name,
      label: m.title,
      color: milestoneColorOf(m.name, colors.value).dot,
      dueX: due ? xOf(due) + px.value / 2 : null,
      spanX: spanStart ? xOf(spanStart) : null,
      spanW: spanStart ? xOf(spanEnd.add(1, "day")) - xOf(spanStart) : 0,
      done: m.status === "Completed",
      collapsible: !!list.length,
      collapsed: folded,
      // The milestone's own bar and diamond stay: folding hides its tasks.
      hidden: folded ? list.length : 0,
      tip: m.title + (due ? " · " + __("due {0}", [due.format("D MMM YYYY")]) : ""),
    });
    if (!folded) out.push(...list.map(taskRow));
  }

  // No milestone, or one this viewer can't see.
  const rest = sortTasks(scheduled.filter((t: any) => !t.milestone || !known.has(t.milestone)));
  if (rest.length) {
    const folded = isCollapsed(NO_MILESTONE);
    out.push({
      key: "g:none",
      kind: "group",
      name: NO_MILESTONE,
      label: __("Not in a milestone"),
      color: null,
      collapsible: true,
      collapsed: folded,
      hidden: folded ? rest.length : 0,
    });
    if (!folded) out.push(...rest.map(taskRow));
  }
  return out;
});

const total = computed(() => items.value.length);
const unscheduled = computed(() => items.value.filter((t: any) => !t.s).length);
</script>
