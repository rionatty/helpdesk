<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideCalendarDays class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Calendar") }}
          </div>
        </div>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-2xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-4 flex-1 overflow-y-auto"
    >
      <div class="executive-card p-4 md:p-5 flex flex-col gap-4">
        <!-- Toolbar -->
        <div class="flex flex-wrap items-center gap-2">
          <Button size="sm" :label="__('Today')" @click="goToday" />
          <div class="flex items-center">
            <Button
              size="sm"
              variant="ghost"
              icon="chevron-left"
              :aria-label="__('Previous')"
              @click="step(-1)"
            />
            <Button
              size="sm"
              variant="ghost"
              icon="chevron-right"
              :aria-label="__('Next')"
              @click="step(1)"
            />
          </div>
          <span class="text-base font-semibold text-ink-gray-9">{{ title }}</span>
          <span class="flex-1" />
          <select
            v-model="agentFilter"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[170px]"
            :aria-label="__('Whose calendar')"
          >
            <option value="">{{ __("Everyone") }}</option>
            <option value="@me">{{ __("Just me") }}</option>
            <option v-for="a in agentOptions" :key="a.value" :value="a.value">
              {{ a.label }}
            </option>
          </select>
          <select
            v-model="typeFilter"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            :aria-label="__('What to show')"
          >
            <option value="">{{ __("Everything") }}</option>
            <option value="Onsite">{{ __("Onsite sessions") }}</option>
            <option value="Online">{{ __("Online sessions") }}</option>
            <option value="Task">{{ __("Other tasks") }}</option>
          </select>
          <div class="inline-flex rounded-md bg-surface-gray-2 p-0.5">
            <button
              v-for="v in VIEWS"
              :key="v.key"
              type="button"
              class="rounded px-2.5 py-1 text-xs"
              :class="
                view === v.key
                  ? 'bg-surface-white text-ink-gray-9 shadow-sm'
                  : 'text-ink-gray-6'
              "
              @click="view = v.key"
            >
              {{ v.label }}
            </button>
          </div>
        </div>

        <!-- Clash summary -->
        <div
          v-if="clashCount"
          class="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
        >
          <LucideAlertTriangle class="size-4 shrink-0" />
          {{
            __(
              "{0} sessions in this view clash — the same person is booked twice. They're outlined in red.",
              [clashCount]
            )
          }}
        </div>

        <div v-if="events.loading && !events.data" class="h-64 rounded-lg bg-surface-gray-2 animate-pulse" />

        <!-- Month -->
        <div v-else-if="view === 'month'" class="overflow-x-auto">
          <div class="min-w-[640px] rounded-lg ring-1 ring-outline-gray-2 overflow-hidden">
            <div class="grid grid-cols-7 bg-surface-gray-1 border-b border-outline-gray-2">
              <div
                v-for="d in WEEKDAYS"
                :key="d"
                class="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5"
              >
                {{ d }}
              </div>
            </div>
            <div class="grid grid-cols-7">
              <div
                v-for="day in monthDays"
                :key="day.key"
                class="min-h-[104px] border-b border-e border-outline-gray-1 p-1.5 flex flex-col gap-1"
                :class="day.inMonth ? 'bg-surface-white' : 'bg-surface-gray-1'"
              >
                <button
                  type="button"
                  class="self-start rounded-full px-1.5 text-xs"
                  :class="
                    day.isToday
                      ? 'bg-blue-600 text-white font-semibold'
                      : day.inMonth
                      ? 'text-ink-gray-7 hover:bg-surface-gray-2'
                      : 'text-ink-gray-4 hover:bg-surface-gray-2'
                  "
                  :title="__('Show this week')"
                  @click="openWeek(day.date)"
                >
                  {{ day.date.date() }}
                </button>
                <button
                  v-for="e in (eventsByDay[day.key] || []).slice(0, MONTH_LIMIT)"
                  :key="e.name"
                  type="button"
                  class="w-full truncate rounded px-1.5 py-0.5 text-start text-[11px] leading-snug"
                  :class="chipClass(e)"
                  :title="tooltip(e)"
                  @click="openTask(e)"
                >
                  <span v-if="e.clashes_with.length" aria-hidden="true">⚠ </span>
                  <span v-if="e.start_time" class="font-semibold">{{ e.start_time }} </span>
                  {{ e.subject }}
                </button>
                <button
                  v-if="(eventsByDay[day.key] || []).length > MONTH_LIMIT"
                  type="button"
                  class="self-start text-[11px] text-ink-gray-5 hover:text-ink-gray-8 hover:underline"
                  @click="openWeek(day.date)"
                >
                  {{ __("+{0} more", [(eventsByDay[day.key] || []).length - MONTH_LIMIT]) }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Week -->
        <div v-else class="grid grid-cols-1 md:grid-cols-7 gap-2">
          <div
            v-for="day in weekDays"
            :key="day.key"
            class="flex flex-col gap-1.5 rounded-lg p-2 min-h-[120px]"
            :class="day.isToday ? 'bg-blue-50 ring-1 ring-blue-200' : 'bg-surface-gray-1'"
          >
            <div class="flex items-baseline gap-1.5 px-0.5">
              <span class="text-xs font-semibold uppercase text-ink-gray-5">
                {{ day.date.format("ddd") }}
              </span>
              <span
                class="text-sm font-semibold"
                :class="day.isToday ? 'text-blue-700' : 'text-ink-gray-8'"
              >
                {{ day.date.format("D MMM") }}
              </span>
            </div>
            <button
              v-for="e in eventsByDay[day.key] || []"
              :key="e.name"
              type="button"
              class="w-full rounded-md px-2 py-1.5 text-start flex flex-col gap-0.5"
              :class="chipClass(e)"
              :title="tooltip(e)"
              @click="openTask(e)"
            >
              <span class="flex items-center gap-1 text-[11px] font-semibold">
                <LucideMapPin v-if="e.session_type === 'Onsite'" class="size-3 shrink-0" />
                <LucideVideo v-else-if="e.session_type === 'Online'" class="size-3 shrink-0" />
                <span>{{ timeLabel(e) }}</span>
                <span v-if="e.clashes_with.length" class="ms-auto">⚠</span>
              </span>
              <span class="text-xs font-medium leading-snug line-clamp-2">{{ e.subject }}</span>
              <span v-if="e.parent_label" class="text-[11px] opacity-80 truncate">
                {{ e.parent_label }}
              </span>
              <span v-if="e.assigned_to_name" class="text-[11px] opacity-80 truncate">
                {{ e.assigned_to_name }}
              </span>
              <span
                v-if="e.session_type === 'Onsite' && e.location"
                class="text-[11px] opacity-80 truncate"
              >
                {{ e.location }}
              </span>
            </button>
            <p
              v-if="!(eventsByDay[day.key] || []).length"
              class="px-0.5 text-[11px] text-ink-gray-4"
            >
              {{ __("Nothing scheduled") }}
            </p>
          </div>
        </div>

        <!-- Legend -->
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-gray-6">
          <span class="inline-flex items-center gap-1">
            <span class="size-2.5 rounded-sm bg-amber-200 ring-1 ring-amber-300" />
            {{ __("Onsite session") }}
          </span>
          <span class="inline-flex items-center gap-1">
            <span class="size-2.5 rounded-sm bg-blue-200 ring-1 ring-blue-300" />
            {{ __("Online session") }}
          </span>
          <span class="inline-flex items-center gap-1">
            <span class="size-2.5 rounded-sm bg-surface-gray-3" />
            {{ __("Other task") }}
          </span>
          <span class="inline-flex items-center gap-1">
            <span class="size-2.5 rounded-sm ring-2 ring-red-500" />
            {{ __("Clash") }}
          </span>
          <span class="ms-auto text-ink-gray-4">
            {{
              __(
                "A session without times takes the whole day. Done and postponed work is faded."
              )
            }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import {
  Button,
  createListResource,
  createResource,
  dayjs,
  usePageMeta,
} from "frappe-ui";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import LucideCalendarDays from "~icons/lucide/calendar-days";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideMapPin from "~icons/lucide/map-pin";
import LucideVideo from "~icons/lucide/video";

usePageMeta(() => ({ title: __("Calendar") }));

const router = useRouter();

const VIEWS = [
  { key: "month", label: __("Month") },
  { key: "week", label: __("Week") },
];
const WEEKDAYS = [
  __("Mon"),
  __("Tue"),
  __("Wed"),
  __("Thu"),
  __("Fri"),
  __("Sat"),
  __("Sun"),
];
const MONTH_LIMIT = 3;
const FMT = "YYYY-MM-DD";

const view = useStorage("hd-calendar-view", "month");
const agentFilter = useStorage("hd-calendar-agent", "");
const typeFilter = useStorage("hd-calendar-type", "");
const cursor = ref(dayjs().startOf("day"));

/** Monday of the week `d` falls in — weeks run Monday to Sunday here. */
function mondayOf(d: any) {
  return d.subtract((d.day() + 6) % 7, "day").startOf("day");
}

const range = computed(() => {
  if (view.value === "week") {
    const start = mondayOf(cursor.value);
    return { start, end: start.add(6, "day") };
  }
  const start = mondayOf(cursor.value.startOf("month"));
  return { start, end: start.add(41, "day") }; // six full weeks
});

const title = computed(() => {
  if (view.value === "week") {
    const { start, end } = range.value;
    return start.month() === end.month()
      ? `${start.format("D")} – ${end.format("D MMM YYYY")}`
      : `${start.format("D MMM")} – ${end.format("D MMM YYYY")}`;
  }
  return cursor.value.format("MMMM YYYY");
});

function step(direction: number) {
  cursor.value =
    view.value === "week"
      ? cursor.value.add(direction * 7, "day")
      : cursor.value.add(direction, "month").startOf("month");
}
function goToday() {
  cursor.value = dayjs().startOf("day");
}
function openWeek(date: any) {
  cursor.value = date;
  view.value = "week";
}

const agents = createListResource({
  doctype: "HD Agent",
  fields: ["name", "agent_name"],
  filters: { is_active: 1 },
  orderBy: "agent_name asc",
  pageLength: 500,
  auto: true,
});
const agentOptions = computed(() =>
  (agents.data || []).map((a: any) => ({
    value: a.name,
    label: a.agent_name || a.name,
  }))
);

const events = createResource({
  url: "helpdesk.api.calendar.get_events",
  makeParams: () => ({
    start: range.value.start.format(FMT),
    end: range.value.end.format(FMT),
    agent: agentFilter.value || undefined,
    session_type: typeFilter.value || undefined,
  }),
  auto: true,
});
watch(
  () => [
    range.value.start.format(FMT),
    range.value.end.format(FMT),
    agentFilter.value,
    typeFilter.value,
  ],
  () => events.reload()
);

const list = computed<any[]>(() => events.data || []);
const clashCount = computed(
  () => list.value.filter((e) => e.clashes_with?.length).length
);

/** Each event on every day it spans inside the view: sessions without times
 * first, then by start time. */
const eventsByDay = computed(() => {
  const out: Record<string, any[]> = {};
  const { start, end } = range.value;
  for (const e of list.value) {
    const first = dayjs(e.start_date || e.end_date);
    const last = dayjs(e.end_date || e.start_date);
    let d = first.isBefore(start) ? start : first;
    const stop = last.isAfter(end) ? end : last;
    while (!d.isAfter(stop, "day")) {
      (out[d.format(FMT)] ||= []).push(e);
      d = d.add(1, "day");
    }
  }
  for (const key of Object.keys(out)) {
    out[key].sort(
      (a, b) =>
        (a.start_time ? 1 : 0) - (b.start_time ? 1 : 0) ||
        (a.start_time || "").localeCompare(b.start_time || "") ||
        (a.subject || "").localeCompare(b.subject || "")
    );
  }
  return out;
});

function days(count: number) {
  const today = dayjs().startOf("day");
  const month = cursor.value.month();
  return Array.from({ length: count }, (_, i) => {
    const date = range.value.start.add(i, "day");
    return {
      key: date.format(FMT),
      date,
      inMonth: date.month() === month,
      isToday: date.isSame(today, "day"),
    };
  });
}
const monthDays = computed(() => days(42));
const weekDays = computed(() => days(7));

function chipClass(e: any) {
  const faded = ["Done", "Postponed"].includes(e.status)
    ? " opacity-50 line-through"
    : "";
  const clash = e.clashes_with?.length ? " ring-2 ring-red-500" : "";
  if (e.session_type === "Onsite")
    return "bg-amber-100 text-amber-900 hover:bg-amber-200" + clash + faded;
  if (e.session_type === "Online")
    return "bg-blue-100 text-blue-900 hover:bg-blue-200" + clash + faded;
  return "bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3" + clash + faded;
}

function timeLabel(e: any) {
  if (e.start_time && e.end_time) return `${e.start_time} – ${e.end_time}`;
  if (e.session_type) return __("All day");
  return __("Task");
}

const byName = computed(() =>
  Object.fromEntries(list.value.map((e: any) => [e.name, e]))
);
function tooltip(e: any) {
  const lines = [
    e.subject,
    [e.session_type ? __(e.session_type) : null, timeLabel(e)]
      .filter(Boolean)
      .join(" · "),
    e.parent_label,
    e.assigned_to_name,
    e.session_type === "Onsite" ? e.location : null,
    e.session_type === "Online" ? e.meeting_link : null,
  ].filter(Boolean);
  if (e.clashes_with?.length) {
    const others = e.clashes_with.map(
      (n: string) => byName.value[n]?.subject || __("another session")
    );
    lines.push(__("Clashes with: {0}", [others.join(", ")]));
  }
  return lines.join("\n");
}

function openTask(e: any) {
  const query = { task: e.name };
  if (e.project)
    router.push({ name: "ProjectAgent", params: { projectId: e.project }, query });
  else if (e.addon)
    router.push({ name: "AddonAgent", params: { addonId: e.addon }, query });
  else router.push({ name: "TasksAgent", query });
}
</script>
