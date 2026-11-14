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
            v-model="projectFilter"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[200px]"
            :aria-label="__('Which project')"
          >
            <option value="">{{ __("All projects") }}</option>
            <option v-for="p in projectList" :key="p.name" :value="p.name">
              {{ p.project_name || p.name }}
            </option>
          </select>
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
          <label
            class="inline-flex items-center gap-1.5 text-sm text-ink-gray-7 cursor-pointer select-none"
          >
            <input v-model="hideDone" type="checkbox" class="rounded" />
            {{ __("Hide done") }}
          </label>
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
          <Button variant="solid" size="sm" @click="openCreate()">
            <template #prefix><LucidePlus class="size-3.5" /></template>
            {{ __("New task") }}
          </Button>
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

        <div
          v-if="events.loading && !events.data"
          class="h-64 rounded-lg bg-surface-gray-2 animate-pulse"
        />

        <!-- Calendar grid: one bar per task, across the days it runs -->
        <div v-else class="overflow-x-auto">
          <div
            class="min-w-[720px] rounded-lg ring-1 ring-outline-gray-2 overflow-hidden select-none"
          >
            <div
              class="grid grid-cols-7 bg-surface-gray-1 border-b border-outline-gray-2"
            >
              <div
                v-for="(d, i) in WEEKDAYS"
                :key="d"
                class="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wide"
                :class="i >= 5 ? 'text-ink-gray-4' : 'text-ink-gray-5'"
              >
                {{ d }}
              </div>
            </div>

            <div
              v-for="week in weeks"
              :key="week.key"
              class="relative border-b border-outline-gray-1 last:border-b-0"
              :style="{ minHeight: view === 'week' ? '380px' : '118px' }"
            >
              <!-- Days: click one, or drag across several, to add a task -->
              <div class="absolute inset-0 grid grid-cols-7">
                <div
                  v-for="day in week.days"
                  :key="day.key"
                  class="border-e border-outline-gray-1 last:border-e-0 cursor-cell transition-colors"
                  :class="dayBackground(day)"
                  :title="__('Click or drag to add a task')"
                  @mousedown.left="startSelect(day)"
                  @mouseenter="extendSelect(day)"
                />
              </div>

              <!-- Day numbers, bars and "+N more" -->
              <div
                class="relative grid grid-cols-7 gap-y-0.5 pb-1.5 pointer-events-none"
                :style="{ gridTemplateRows: rowTemplate(week) }"
              >
                <div
                  v-for="(day, i) in week.days"
                  :key="'n' + day.key"
                  class="px-1.5 pt-1"
                  :style="{ gridColumn: i + 1, gridRow: 1 }"
                >
                  <button
                    type="button"
                    class="pointer-events-auto rounded-full px-1.5 text-xs"
                    :class="
                      day.isToday
                        ? 'bg-blue-600 text-white font-semibold'
                        : day.inMonth
                        ? 'text-ink-gray-7 hover:bg-surface-gray-3'
                        : 'text-ink-gray-4 hover:bg-surface-gray-3'
                    "
                    :title="__('Show this week')"
                    @mousedown.stop
                    @click.stop="openWeek(day.date)"
                  >
                    {{ day.date.format(view === "week" ? "ddd D MMM" : "D") }}
                  </button>
                </div>

                <button
                  v-for="seg in week.shown"
                  :key="week.key + seg.item.name"
                  type="button"
                  class="pointer-events-auto mx-1 flex min-w-0 flex-col justify-center overflow-hidden px-1.5 text-start leading-tight hover:brightness-95"
                  :class="barClass(seg)"
                  :style="barStyle(seg)"
                  :title="tooltip(seg.item)"
                  @mousedown.stop
                  @click.stop="openPeek(seg.item)"
                >
                  <span class="flex min-w-0 items-center gap-1 text-[11px]">
                    <LucideMapPin
                      v-if="seg.item.session_type === 'Onsite'"
                      class="size-3 shrink-0"
                    />
                    <LucideVideo
                      v-else-if="seg.item.session_type === 'Online'"
                      class="size-3 shrink-0"
                    />
                    <span v-if="seg.item.start_time" class="shrink-0 font-semibold">
                      {{ seg.item.start_time }}
                    </span>
                    <span class="truncate font-medium">{{ seg.item.subject }}</span>
                    <span
                      v-if="seg.item.clashes_with.length"
                      class="ms-auto shrink-0"
                      aria-hidden="true"
                    >⚠</span>
                  </span>
                  <span
                    v-if="view === 'week'"
                    class="truncate text-[10px] opacity-80"
                  >
                    {{
                      [seg.item.parent_label, seg.item.assigned_to_name]
                        .filter(Boolean)
                        .join(" · ")
                    }}
                  </span>
                </button>

                <button
                  v-for="m in week.more"
                  :key="'m' + m.day.key"
                  type="button"
                  class="pointer-events-auto mx-1.5 self-start text-start text-[11px] text-ink-gray-5 hover:text-ink-gray-8 hover:underline"
                  :style="{ gridColumn: m.index + 1, gridRow: week.lanes + 2 }"
                  @mousedown.stop
                  @click.stop="openWeek(m.day.date)"
                >
                  {{ __("+{0} more", [m.count]) }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div
          class="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-ink-gray-6"
        >
          <span
            v-for="p in projectsInView"
            :key="p.name"
            class="inline-flex items-center gap-1"
          >
            <span class="size-2.5 rounded-sm" :style="{ background: p.color.dot }" />
            {{ p.label }}
          </span>
          <span class="inline-flex items-center gap-1">
            <LucideMapPin class="size-3" /> {{ __("Onsite") }}
          </span>
          <span class="inline-flex items-center gap-1">
            <LucideVideo class="size-3" /> {{ __("Online") }}
          </span>
          <span class="inline-flex items-center gap-1">
            <span class="size-2.5 rounded-sm ring-2 ring-red-500" />
            {{ __("Clash") }}
          </span>
          <span class="ms-auto text-ink-gray-4">
            {{ __("Click a day, or drag across days, to add a task.") }}
          </span>
        </div>
      </div>
    </div>

    <!-- New task -->
    <Dialog
      v-model="showCreate"
      :options="{ title: __('New task'), size: 'xl' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Project") }} *</span>
              <select v-model="form.project" :class="INPUT">
                <option value="" disabled>{{ __("Choose a project") }}</option>
                <option v-for="p in projectList" :key="p.name" :value="p.name">
                  {{ p.project_name || p.name
                  }}{{ p.customer ? " · " + p.customer : "" }}
                </option>
              </select>
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Milestone") }}</span>
              <select
                v-model="form.milestone"
                :class="INPUT"
                :disabled="!form.project || !milestoneOptions.length"
              >
                <option value="">
                  {{
                    form.project && !milestoneOptions.length
                      ? __("This project has no milestones")
                      : __("None")
                  }}
                </option>
                <option v-for="m in milestoneOptions" :key="m.name" :value="m.name">
                  {{ m.title }}
                </option>
              </select>
            </label>
          </div>

          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Title") }} *</span>
            <input
              ref="subjectInput"
              v-model="form.subject"
              type="text"
              maxlength="500"
              :placeholder="__('What needs doing?')"
              :class="INPUT"
              @keydown.enter.prevent="submitCreate"
            />
          </label>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Start") }}</span>
              <input v-model="form.start_date" type="date" :class="INPUT" />
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Due") }}</span>
              <input
                v-model="form.end_date"
                type="date"
                :min="form.start_date"
                :class="INPUT"
              />
            </label>
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Assigned to") }}</span>
              <select v-model="form.assigned_to" :class="INPUT">
                <option value="">{{ __("Unassigned") }}</option>
                <option v-for="a in agentOptions" :key="a.value" :value="a.value">
                  {{ a.label }}
                </option>
              </select>
            </label>
          </div>

          <!-- Session: Onsite at the client, or Online -->
          <div class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-3">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs text-ink-gray-5 me-1">{{ __("Session") }}</span>
              <button
                v-for="s in SESSION_CHOICES"
                :key="s.value"
                type="button"
                class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs"
                :class="
                  form.session_type === s.value
                    ? s.active
                    : 'border-outline-gray-2 bg-surface-white text-ink-gray-6 hover:bg-surface-gray-2'
                "
                @click="form.session_type = s.value"
              >
                <component :is="s.icon" v-if="s.icon" class="size-3" />
                {{ s.label }}
              </button>
            </div>
            <template v-if="form.session_type">
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label class="flex flex-col gap-1">
                  <span class="text-xs text-ink-gray-5">{{ __("From") }}</span>
                  <input v-model="form.start_time" type="time" :class="INPUT" />
                </label>
                <label class="flex flex-col gap-1">
                  <span class="text-xs text-ink-gray-5">{{ __("To") }}</span>
                  <input v-model="form.end_time" type="time" :class="INPUT" />
                </label>
                <label
                  v-if="form.session_type === 'Onsite'"
                  class="flex flex-col gap-1"
                >
                  <span class="text-xs text-ink-gray-5">{{ __("Location") }}</span>
                  <input
                    v-model="form.location"
                    type="text"
                    :placeholder="__('Client site, office…')"
                    :class="INPUT"
                  />
                </label>
                <label v-else class="flex flex-col gap-1">
                  <span class="text-xs text-ink-gray-5">{{ __("Meeting link") }}</span>
                  <input
                    v-model="form.meeting_link"
                    type="url"
                    :placeholder="__('https://meet.google.com/…')"
                    :class="INPUT"
                  />
                </label>
              </div>
              <span class="text-[11px] text-ink-gray-5">
                {{ __("Leave the times empty for a session that takes the whole day.") }}
              </span>
            </template>
          </div>

          <!-- Checked before saving: would this double-book them? -->
          <div
            v-if="proposedClashes.length || proposedHidden"
            class="flex flex-col gap-1 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800"
          >
            <span class="inline-flex items-center gap-1 font-semibold">
              <LucideAlertTriangle class="size-3.5" />
              {{ __("{0} already has a session then", [assigneeName(form.assigned_to)]) }}
            </span>
            <span v-for="c in proposedClashes" :key="c.name">
              {{ c.subject
              }}<template v-if="c.parent_label"> · {{ c.parent_label }}</template>
              · {{ formatDay(c.start_date) }} {{ timeLabel(c) }}
            </span>
            <span v-if="proposedHidden">
              {{ __("+{0} more in projects you are not on", [proposedHidden]) }}
            </span>
          </div>

          <label class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Description") }}</span>
            <textarea
              v-model="form.description"
              rows="2"
              :placeholder="__('Details, agenda, what the client should prepare…')"
              :class="INPUT + ' resize-y'"
            />
          </label>

          <p v-if="tried && formError" class="text-xs text-red-700">{{ formError }}</p>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-2 w-full">
          <Button :label="__('Cancel')" @click="showCreate = false" />
          <Button
            class="flex-1"
            variant="solid"
            :label="__('Add task')"
            :loading="createRes.loading"
            @click="submitCreate"
          />
        </div>
      </template>
    </Dialog>

    <!-- Quick view of a task, without leaving the calendar -->
    <Dialog
      v-model="showPeek"
      :options="{ title: peek?.subject || __('Task'), size: 'lg' }"
    >
      <template #body-content>
        <div v-if="peek" class="flex flex-col gap-3 text-sm">
          <div v-if="peek.parent_label" class="flex items-center gap-2">
            <span
              class="size-2.5 rounded-sm"
              :style="{ background: colorOf(peek).dot }"
            />
            <span class="font-medium text-ink-gray-8">{{ peek.parent_label }}</span>
            <span v-if="peek.customer" class="text-ink-gray-5">· {{ peek.customer }}</span>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs text-ink-gray-5">{{ __("When") }}</span>
              <span class="text-ink-gray-8">{{ dateRange(peek) }}</span>
              <span v-if="peek.session_type" class="text-xs text-ink-gray-6">
                {{ timeLabel(peek) }}
              </span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-xs text-ink-gray-5">{{ __("Assigned to") }}</span>
              <span class="text-ink-gray-8">{{ peek.assigned_to_name || "—" }}</span>
            </div>
            <div v-if="peek.session_type" class="flex flex-col gap-0.5 col-span-2">
              <span class="text-xs text-ink-gray-5">
                {{
                  peek.session_type === "Onsite"
                    ? __("Onsite session")
                    : __("Online session")
                }}
              </span>
              <span
                v-if="peek.session_type === 'Onsite'"
                class="inline-flex items-center gap-1 text-ink-gray-8"
              >
                <LucideMapPin class="size-3.5" />
                {{ peek.location || __("No location given") }}
              </span>
              <a
                v-else-if="webLink(peek.meeting_link)"
                :href="webLink(peek.meeting_link)"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 text-blue-600 hover:underline"
              >
                <LucideVideo class="size-3.5" /> {{ __("Join the meeting") }}
              </a>
              <span v-else class="text-ink-gray-5">{{ __("No meeting link yet") }}</span>
            </div>
            <label class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Status") }}</span>
              <select
                :value="peek.status"
                :class="INPUT"
                @change="(e) => setStatus(e.target.value)"
              >
                <option v-for="s in STATUSES" :key="s" :value="s">{{ __(s) }}</option>
              </select>
            </label>
          </div>

          <div
            v-if="peek.clashes_with?.length"
            class="flex flex-col gap-1 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800"
          >
            <span class="inline-flex items-center gap-1 font-semibold">
              <LucideAlertTriangle class="size-3.5" />
              {{ __("Clashes with") }}
            </span>
            <span v-for="n in peek.clashes_with" :key="n">
              {{ byName[n]?.subject || __("another session") }}
            </span>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-2 w-full">
          <Button :label="__('Close')" @click="showPeek = false" />
          <Button class="flex-1" variant="solid" @click="openTask(peek)">
            <template #prefix><LucideExternalLink class="size-3.5" /></template>
            {{ __("Open task") }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useEventListener, useStorage, watchDebounced } from "@vueuse/core";
import {
  Button,
  Dialog,
  createListResource,
  createResource,
  dayjs,
  toast,
  usePageMeta,
} from "frappe-ui";
import { LayoutHeader } from "@/components";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import { buildMilestoneColors, milestoneColorOf } from "@/utils";
import {
  hiddenPerDay,
  layoutWeek,
  type Segment,
} from "@/composables/calendarLayout";
import LucideCalendarDays from "~icons/lucide/calendar-days";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideMapPin from "~icons/lucide/map-pin";
import LucideVideo from "~icons/lucide/video";
import LucidePlus from "~icons/lucide/plus";
import LucideExternalLink from "~icons/lucide/external-link";

usePageMeta(() => ({ title: __("Calendar") }));

const router = useRouter();
const { userId } = useAuthStore();

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
const STATUSES = ["To Do", "In Progress", "Pending", "Postponed", "Done"];
const SESSION_CHOICES = [
  { value: "", label: __("Not a session"), icon: null, active: "border-ink-gray-7 bg-surface-white text-ink-gray-9" },
  { value: "Onsite", label: __("Onsite"), icon: LucideMapPin, active: "border-amber-400 bg-amber-50 text-amber-900" },
  { value: "Online", label: __("Online"), icon: LucideVideo, active: "border-blue-400 bg-blue-50 text-blue-900" },
];
const INPUT =
  "text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400 disabled:opacity-60";
const MONTH_LANES = 4;
const FMT = "YYYY-MM-DD";

// --- View, filters (remembered per browser) --------------------------------
const view = useStorage("hd-calendar-view", "month");
const agentFilter = useStorage("hd-calendar-agent", "");
const typeFilter = useStorage("hd-calendar-type", "");
const projectFilter = useStorage("hd-calendar-project", "");
const hideDone = useStorage("hd-calendar-hide-done", false);
const lastProject = useStorage("hd-calendar-last-project", "");
const cursor = ref(dayjs().startOf("day"));

/** Monday of the week `d` falls in - weeks run Monday to Sunday here. */
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

// --- People and projects ---------------------------------------------------
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
function assigneeName(id: string) {
  return agentOptions.value.find((a) => a.value === id)?.label || __("They");
}

// The projects this agent can work in - managers see them all.
const projects = createResource({
  url: "helpdesk.api.project.get_projects",
  auto: true,
});
const projectList = computed<any[]>(() =>
  [...(projects.data || [])].sort((a: any, b: any) =>
    (a.project_name || a.name).localeCompare(b.project_name || b.name)
  )
);
// A project keeps its colour from month to month: the palette follows the
// sorted list of every project, not just the ones on screen.
const projectColors = computed(() =>
  buildMilestoneColors(projectList.value.map((p: any) => p.name))
);
function colorOf(e: any) {
  return milestoneColorOf(e?.project, projectColors.value);
}

// --- Events ----------------------------------------------------------------
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

const visibleEvents = computed<any[]>(() =>
  (events.data || []).filter(
    (e: any) =>
      (!projectFilter.value || e.project === projectFilter.value) &&
      (!hideDone.value || !["Done", "Postponed"].includes(e.status))
  )
);
const byName = computed(() =>
  Object.fromEntries((events.data || []).map((e: any) => [e.name, e]))
);
const clashCount = computed(
  () => visibleEvents.value.filter((e) => e.clashes_with?.length).length
);
const projectsInView = computed(() => {
  const seen = new Map<string, any>();
  for (const e of visibleEvents.value) {
    if (e.project && !seen.has(e.project))
      seen.set(e.project, {
        name: e.project,
        label: e.parent_label || e.project,
        color: colorOf(e),
      });
  }
  return [...seen.values()];
});

const weeks = computed(() => {
  const count = view.value === "week" ? 1 : 6;
  const today = dayjs().startOf("day");
  const month = cursor.value.month();
  return Array.from({ length: count }, (_, w) => {
    const start = range.value.start.add(w * 7, "day");
    const days = Array.from({ length: 7 }, (_, i) => {
      const date = start.add(i, "day");
      return {
        key: date.format(FMT),
        date,
        inMonth: view.value === "week" || date.month() === month,
        isToday: date.isSame(today, "day"),
        isWeekend: i >= 5,
      };
    });
    const { segments, laneCount } = layoutWeek(
      visibleEvents.value,
      start.format(FMT)
    );
    const cap = view.value === "week" ? laneCount : MONTH_LANES;
    const more =
      view.value === "week"
        ? []
        : hiddenPerDay(segments, MONTH_LANES)
            .map((count, index) => ({ count, index, day: days[index] }))
            .filter((m) => m.count);
    return {
      key: start.format(FMT),
      days,
      shown: segments.filter((s) => s.lane < cap),
      lanes: Math.min(laneCount, cap),
      more,
    };
  });
});

function rowTemplate(week: any) {
  const lane = view.value === "week" ? "40px" : "22px";
  const lanes = week.lanes ? ` repeat(${week.lanes}, ${lane})` : "";
  return `28px${lanes}${week.more.length ? " 18px" : ""}`;
}

function dayBackground(day: any) {
  if (isSelected(day)) return "bg-blue-100";
  if (day.isToday) return "bg-blue-50/60 hover:bg-blue-50";
  if (!day.inMonth) return "bg-surface-gray-2 hover:bg-surface-gray-3";
  if (day.isWeekend) return "bg-surface-gray-1 hover:bg-surface-gray-2";
  return "bg-surface-white hover:bg-surface-gray-1";
}

function barStyle(seg: Segment) {
  const c = colorOf(seg.item);
  return {
    gridColumn: `${seg.start + 1} / span ${seg.span}`,
    gridRow: seg.lane + 2,
    background: c.bg,
    color: c.text,
    borderLeft: seg.continuesBefore ? undefined : `3px solid ${c.dot}`,
  };
}
function barClass(seg: Segment) {
  return [
    // A bar carried over from the previous week (or on into the next) has
    // a square end there, so it reads as one continuing task.
    seg.continuesBefore ? "rounded-l-none" : "rounded-l",
    seg.continuesAfter ? "rounded-r-none" : "rounded-r",
    seg.item.clashes_with?.length ? "ring-2 ring-red-500 ring-inset" : "",
    ["Done", "Postponed"].includes(seg.item.status)
      ? "opacity-50 line-through"
      : "",
  ];
}

// --- Words for times and dates ---------------------------------------------
function timeLabel(e: any) {
  if (e.start_time && e.end_time) return `${e.start_time} – ${e.end_time}`;
  if (e.session_type) return __("All day");
  return "";
}
function formatDay(value: string) {
  return value ? dayjs(value).format("ddd D MMM") : "";
}
function dateRange(e: any) {
  const first = e.start_date || e.end_date;
  const last = e.end_date || e.start_date;
  if (!first) return "—";
  return first === last
    ? formatDay(first)
    : `${dayjs(first).format("D MMM")} – ${dayjs(last).format("D MMM YYYY")}`;
}
function tooltip(e: any) {
  const lines = [
    e.subject,
    [dateRange(e), timeLabel(e)].filter(Boolean).join(" · "),
    [e.session_type ? __(e.session_type) : null, e.parent_label]
      .filter(Boolean)
      .join(" · "),
    e.assigned_to_name,
  ].filter(Boolean);
  if (e.clashes_with?.length) {
    const others = e.clashes_with.map(
      (n: string) => byName.value[n]?.subject || __("another session")
    );
    lines.push(__("Clashes with: {0}", [others.join(", ")]));
  }
  return lines.join("\n");
}
/** A meeting link is only ever a web link - never script. */
function webLink(url: string | null | undefined): string | null {
  const value = (url || "").trim();
  const lower = value.toLowerCase();
  return lower.startsWith("https://") || lower.startsWith("http://")
    ? value
    : null;
}

// --- Click a day, or drag across days, to add a task -----------------------
const selection = ref<{ anchor: string; current: string } | null>(null);
const selectedRange = computed(() => {
  if (!selection.value) return null;
  const [start, end] = [selection.value.anchor, selection.value.current].sort();
  return { start, end };
});
function isSelected(day: any) {
  const r = selectedRange.value;
  return !!r && day.key >= r.start && day.key <= r.end;
}
function startSelect(day: any) {
  selection.value = { anchor: day.key, current: day.key };
}
function extendSelect(day: any) {
  if (selection.value) selection.value.current = day.key;
}
useEventListener(window, "mouseup", () => {
  const r = selectedRange.value;
  selection.value = null;
  if (r) openCreate(r.start, r.end);
});

// --- New task ----------------------------------------------------------------
const showCreate = ref(false);
const tried = ref(false);
const subjectInput = ref<HTMLInputElement | null>(null);
const form = reactive({
  project: "",
  milestone: "",
  subject: "",
  start_date: "",
  end_date: "",
  assigned_to: "",
  session_type: "",
  start_time: "",
  end_time: "",
  location: "",
  meeting_link: "",
  description: "",
});

function defaultProject() {
  const known = (name: string) => projectList.value.some((p: any) => p.name === name);
  if (projectFilter.value && known(projectFilter.value)) return projectFilter.value;
  if (lastProject.value && known(lastProject.value)) return lastProject.value;
  return projectList.value.length === 1 ? projectList.value[0].name : "";
}
function defaultAssignee() {
  if (agentFilter.value && agentFilter.value !== "@me") return agentFilter.value;
  return agentOptions.value.some((a) => a.value === userId) ? userId : "";
}

function openCreate(start?: string, end?: string) {
  const first = start || dayjs().format(FMT);
  Object.assign(form, {
    project: defaultProject(),
    milestone: "",
    subject: "",
    start_date: first,
    end_date: end || first,
    assigned_to: defaultAssignee(),
    session_type: "",
    start_time: "",
    end_time: "",
    location: "",
    meeting_link: "",
    description: "",
  });
  tried.value = false;
  clashCheck.data = null;
  showCreate.value = true;
  nextTick(() => subjectInput.value?.focus());
}

const milestones = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: form.project }),
});
const milestoneOptions = computed<any[]>(() =>
  form.project ? milestones.data || [] : []
);
watch(
  () => form.project,
  (project) => {
    form.milestone = "";
    if (project) milestones.reload();
  }
);

// Would this double-book the assignee? Asked as the form is filled in.
const clashCheck = createResource({ url: "helpdesk.api.calendar.check_clashes" });
const proposedClashes = computed<any[]>(() =>
  showCreate.value ? clashCheck.data?.clashes || [] : []
);
const proposedHidden = computed<number>(() =>
  showCreate.value ? clashCheck.data?.hidden || 0 : 0
);
watchDebounced(
  () => [
    showCreate.value,
    form.assigned_to,
    form.session_type,
    form.start_date,
    form.end_date,
    form.start_time,
    form.end_time,
  ],
  () => {
    if (
      !showCreate.value ||
      !form.session_type ||
      !form.assigned_to ||
      !form.start_date
    ) {
      clashCheck.data = null;
      return;
    }
    clashCheck.submit({
      assigned_to: form.assigned_to,
      session_type: form.session_type,
      start_date: form.start_date,
      end_date: form.end_date || form.start_date,
      start_time: form.start_time || undefined,
      end_time: form.end_time || undefined,
    });
  },
  { debounce: 350 }
);

const formError = computed(() => {
  if (!form.project) return __("Choose a project.");
  if (!form.subject.trim()) return __("Give the task a title.");
  if (!form.start_date) return __("Pick a start date.");
  if (form.end_date && form.end_date < form.start_date)
    return __("The due date is before the start date.");
  if (
    form.session_type &&
    form.start_time &&
    form.end_time &&
    (form.end_date || form.start_date) === form.start_date &&
    form.end_time <= form.start_time
  )
    return __("The session ends before it starts.");
  return "";
});

const createRes = createResource({
  url: "helpdesk.api.addon.add_task",
  onSuccess: () => {
    lastProject.value = form.project;
    showCreate.value = false;
    const project = projectList.value.find((p: any) => p.name === form.project);
    toast.success(
      __("Task added to {0}", [project?.project_name || form.project])
    );
    events.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not add the task")),
});
function submitCreate() {
  tried.value = true;
  if (formError.value || createRes.loading) return;
  const session = form.session_type;
  createRes.submit({
    project: form.project,
    milestone: form.milestone || undefined,
    subject: form.subject.trim(),
    start_date: form.start_date,
    end_date: form.end_date || form.start_date,
    assigned_to: form.assigned_to || undefined,
    description: form.description.trim() || undefined,
    session_type: session || undefined,
    start_time: (session && form.start_time) || undefined,
    end_time: (session && form.end_time) || undefined,
    location: (session === "Onsite" && form.location.trim()) || undefined,
    meeting_link: (session === "Online" && form.meeting_link.trim()) || undefined,
  });
}

// --- Quick view ------------------------------------------------------------
const peek = ref<any>(null);
const showPeek = computed({
  get: () => !!peek.value,
  set: (open: boolean) => {
    if (!open) peek.value = null;
  },
});
function openPeek(e: any) {
  peek.value = { ...e };
}

const statusRes = createResource({
  url: "helpdesk.api.addon.update_task",
  onSuccess: () => {
    toast.success(__("Status updated"));
    events.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update the task")),
});
function setStatus(status: string) {
  if (!peek.value || peek.value.status === status) return;
  peek.value = { ...peek.value, status };
  statusRes.submit({ name: peek.value.name, status });
}

function openTask(e: any) {
  if (!e) return;
  const query = { task: e.name };
  if (e.project)
    router.push({ name: "ProjectAgent", params: { projectId: e.project }, query });
  else if (e.addon)
    router.push({ name: "AddonAgent", params: { addonId: e.addon }, query });
  else router.push({ name: "TasksAgent", query });
}
</script>
