<template>
  <!-- Hidden entirely for customers when there are no visible subtasks. -->
  <div v-if="editable || (subtasks.data && subtasks.data.length)" class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <div
        class="size-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center shadow-sm ring-1 ring-inset ring-white/40"
      >
        <LucideListTodo class="size-4 text-white" />
      </div>
      <span class="text-sm font-semibold text-ink-gray-8">{{ __("Subtasks") }}</span>
      <span
        v-if="summary.total"
        class="text-xs font-semibold text-violet-700 bg-violet-100 rounded-full px-2 py-0.5"
      >
        {{ summary.done }}/{{ summary.total }} {{ __("done") }}
      </span>
      <span class="flex-1" />
      <span
        v-if="summary.avg_score"
        class="text-xs font-medium text-amber-700 inline-flex items-center gap-0.5"
        :title="__('Average review score')"
      >
        <LucideStar class="size-3 fill-amber-500 text-amber-500" />
        {{ summary.avg_score }}/5
      </span>
    </div>

    <!-- Progress bar -->
    <div v-if="summary.total" class="flex flex-col gap-1.5">
      <div class="flex h-2 w-full rounded-full bg-surface-gray-2 overflow-hidden">
        <div
          class="h-full bg-gradient-to-r from-violet-500 to-blue-500 transition-[width] duration-500"
          :style="{ width: pct(summary.done) }"
        />
        <div
          class="h-full bg-blue-300 transition-[width] duration-500"
          :style="{ width: pct(summary.in_progress) }"
        />
      </div>
      <div class="flex items-center justify-between text-xs text-ink-gray-6">
        <span>{{ summary.progress }}% {{ __("complete") }}</span>
        <div class="flex items-center gap-2.5">
          <span
            v-if="summary.overdue"
            class="inline-flex items-center gap-1 text-ink-red-3 font-medium"
          >
            <LucideAlertTriangle class="size-3" />
            {{ summary.overdue }} {{ __("overdue") }}
          </span>
          <span v-if="summary.hours_spent">
            {{ formatHours(summary.hours_spent) }} {{ __("logged") }}
          </span>
        </div>
      </div>
    </div>

    <!-- Estimate vs actual (from the parent task's estimate) -->
    <div
      v-if="editable && (estimatedHours || summary.hours_spent)"
      class="flex items-center justify-between text-xs px-0.5"
      :class="overBudget ? 'text-ink-red-3 font-medium' : 'text-ink-gray-6'"
    >
      <span>
        {{ formatHours(summary.hours_spent) }} {{ __("logged") }}
        <template v-if="estimatedHours">
          / {{ formatHours(estimatedHours) }} {{ __("estimated") }}
        </template>
      </span>
      <span v-if="overBudget">{{ __("over budget") }}</span>
    </div>

    <!-- Filters (agent view, long lists only).
         View-only: narrowing the list changes nothing that is saved, and the
         chip, progress bar and hours above keep covering ALL subtasks — only
         the rows below are filtered. -->
    <div v-if="showFilters" class="flex flex-wrap items-center gap-2">
      <select
        v-model="statusFilter"
        class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
        :aria-label="__('Filter by status')"
      >
        <option value="">{{ __("All statuses") }}</option>
        <option value="To Do">{{ __("To Do") }}</option>
        <option value="In Progress">{{ __("In Progress") }}</option>
        <option value="Done">{{ __("Done") }}</option>
      </select>
      <select
        v-if="filterAssigneeOptions.length || hasUnassigned"
        v-model="assigneeFilter"
        class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[120px]"
        :aria-label="__('Filter by assignee')"
      >
        <option value="">{{ __("All assignees") }}</option>
        <option v-if="hasUnassigned" value="__unassigned__">
          {{ __("Unassigned") }}
        </option>
        <option v-for="a in filterAssigneeOptions" :key="a.value" :value="a.value">
          {{ a.label }}
        </option>
      </select>
      <!-- Only offered once the rows actually carry a responsibility. -->
      <select
        v-if="hasResponsibility"
        v-model="responsibilityFilter"
        class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
        :aria-label="__('Filter by responsibility')"
      >
        <option value="">{{ __("All responsibilities") }}</option>
        <option v-for="r in RESPONSIBILITIES" :key="r" :value="r">
          {{ respLabel(r) }}
        </option>
      </select>
      <span
        v-if="anyFilterActive"
        class="text-xs text-ink-gray-5"
        :title="__('The counts and progress above still cover every subtask')"
      >
        {{ __("showing {0} of {1}", [visibleSubtasks.length, subtasks.data.length]) }}
      </span>
      <button
        v-if="anyFilterActive"
        type="button"
        class="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-0.5 px-1"
        @click="clearFilters"
      >
        <LucideX class="size-3" /> {{ __("Clear") }}
      </button>
    </div>

    <!-- Subtask list -->
    <div v-if="visibleSubtasks.length" class="flex flex-col gap-2">
      <div
        v-for="t in visibleSubtasks"
        :key="t.name"
        class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5 flex flex-col gap-2"
      >
        <div class="flex items-start gap-2">
          <component
            :is="statusIcon(t.status)"
            class="size-4 mt-0.5 shrink-0"
            :class="statusColor(t.status)"
          />
          <!-- Agents rename in place; the customer view stays read-only text. -->
          <input
            v-if="editable"
            type="text"
            :value="t.subject"
            maxlength="500"
            :aria-label="__('Subtask subject')"
            :title="__('Rename this subtask')"
            class="flex-1 min-w-0 text-sm leading-snug font-medium bg-transparent rounded-md border border-transparent px-1.5 py-0.5 hover:border-outline-gray-2 focus:border-blue-400 focus:bg-surface-white focus:outline-none"
            :class="t.status === 'Done' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
            @change="(e) => renameSubtask(t, e.target)"
            @keyup.enter="(e) => e.target.blur()"
          />
          <span
            v-else
            class="text-sm flex-1 leading-snug font-medium"
            :class="t.status === 'Done' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
          >
            {{ t.subject }}
          </span>
          <!-- Who does the work. Internal: scrubbed from the customer payload. -->
          <span
            v-if="editable && t.responsibility"
            class="text-[10px] font-medium rounded-full px-1.5 py-0.5 shrink-0"
            :class="respClass(t.responsibility)"
            :title="__('Who does this work')"
          >
            {{ respLabel(t.responsibility) }}
          </span>
          <span
            v-if="Number(t.score)"
            class="text-[10px] rounded-full px-1.5 py-0.5 bg-amber-100 text-amber-700 inline-flex items-center gap-0.5 shrink-0"
          >
            <LucideStar class="size-3 fill-amber-500 text-amber-500" /> {{ t.score }}/5
          </span>
          <button
            v-if="editable"
            type="button"
            class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
            :aria-label="__('Delete subtask')"
            @click="removeSubtask(t.name)"
          >
            <LucideTrash2 class="size-3.5" />
          </button>
        </div>

        <!-- Read-only assignee + due (customer view) -->
        <div
          v-if="!editable && (t.assigned_to_name || t.due_date)"
          class="flex flex-wrap items-center gap-x-3 gap-y-1 ps-6 text-xs"
        >
          <span v-if="t.assigned_to_name" class="flex items-center gap-1.5 text-ink-gray-6">
            <Avatar size="xs" :label="t.assigned_to_name" />
            {{ t.assigned_to_name }}
          </span>
          <span
            v-if="t.due_date"
            class="flex items-center gap-1"
            :class="isOverdue(t) ? 'text-ink-red-3 font-medium' : 'text-ink-gray-6'"
          >
            <LucideCalendarClock class="size-3.5" />
            {{ dayjs(t.due_date).format("MMM D") }}
          </span>
        </div>

        <!-- Controls -->
        <div v-if="editable" class="flex flex-wrap items-center gap-2 ps-6">
          <select
            :value="t.status"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            @change="(e) => patchSubtask(t, { status: e.target.value })"
          >
            <option value="To Do">{{ __("To Do") }}</option>
            <option value="In Progress">{{ __("In Progress") }}</option>
            <option value="Done">{{ __("Done") }}</option>
          </select>
          <!-- Who does the work — not the same thing as customer visibility. -->
          <select
            :value="t.responsibility || 'Us'"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            :aria-label="__('Responsibility')"
            :title="__('Who does this work — us, the client, or both')"
            @change="(e) => patchSubtask(t, { responsibility: e.target.value })"
          >
            <option v-for="r in RESPONSIBILITIES" :key="r" :value="r">
              {{ respLabel(r) }}
            </option>
          </select>
          <select
            :value="t.assigned_to || ''"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[120px]"
            :aria-label="__('Assignee')"
            @change="(e) => patchSubtask(t, { assigned_to: e.target.value })"
          >
            <option value="">{{ __("Unassigned") }}</option>
            <option v-for="a in agentOptions" :key="a.value" :value="a.value">
              {{ a.label }}
            </option>
          </select>
          <select
            :value="t.reviewer || ''"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[120px]"
            :aria-label="__('Reviewer')"
            @change="(e) => patchSubtask(t, { reviewer: e.target.value })"
          >
            <option value="">{{ __("No reviewer") }}</option>
            <option v-for="a in agentOptions" :key="a.value" :value="a.value">
              {{ a.label }}
            </option>
          </select>
          <div class="flex items-center gap-1">
            <LucideClock class="size-3.5 text-ink-gray-5" />
            <input
              type="number"
              min="0"
              step="0.25"
              :value="t.hours_spent"
              class="w-14 text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              :aria-label="__('Hours spent')"
              @change="(e) => patchSubtask(t, { hours_spent: parseFloat(e.target.value) || 0 })"
            />
            <span class="text-xs text-ink-gray-5">{{ __("hrs") }}</span>
          </div>
          <div class="flex items-center gap-1">
            <LucideCalendarClock
              class="size-3.5"
              :class="isOverdue(t) ? 'text-ink-red-3' : 'text-ink-gray-5'"
            />
            <input
              type="date"
              :value="t.due_date || ''"
              class="text-xs rounded-md border bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
              :class="isOverdue(t) ? 'border-red-300 text-ink-red-3' : 'border-outline-gray-2 text-ink-gray-7'"
              :aria-label="__('Due date')"
              @change="(e) => patchSubtask(t, { due_date: e.target.value })"
            />
          </div>
          <label
            class="flex items-center gap-1.5 text-xs text-ink-gray-6 cursor-pointer"
            :title="__('Show this subtask to the customer')"
          >
            <input
              type="checkbox"
              :checked="!!t.customer_visible"
              @change="(e) => patchSubtask(t, { customer_visible: e.target.checked ? 1 : 0 })"
            />
            {{ __("Client-visible") }}
          </label>
        </div>

        <!-- Review score -->
        <div v-if="editable" class="flex items-center gap-2 ps-6">
          <span class="text-xs text-ink-gray-5">
            {{ __("Score") }}
            <template v-if="!canScore(t)">
              ·
              {{ t.reviewer ? __("reviewer only") : __("set a reviewer") }}
            </template>
          </span>
          <div class="flex items-center gap-0.5">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              :disabled="!canScore(t)"
              :class="canScore(t) ? 'cursor-pointer hover:scale-110 transition-transform' : 'cursor-default'"
              :aria-label="__('Score {0} of 5', [n])"
              @click="canScore(t) && patchSubtask(t, { score: n === Number(t.score) ? 0 : n })"
            >
              <LucideStar
                class="size-4"
                :class="n <= (Number(t.score) || 0) ? 'text-amber-400 fill-amber-400' : 'text-ink-gray-3'"
              />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Everything filtered out: the subtasks are still there, just hidden. -->
    <div
      v-else-if="subtasks.data && subtasks.data.length"
      class="flex items-center gap-2 text-xs text-ink-gray-5 px-1"
    >
      {{ __("No subtasks match these filters.") }}
      <button
        type="button"
        class="text-blue-600 hover:text-blue-700 font-medium"
        @click="clearFilters"
      >
        {{ __("Clear") }}
      </button>
    </div>

    <div v-else-if="!subtasks.loading" class="text-xs text-ink-gray-5 px-1">
      {{ __("No subtasks yet — break this task into steps below.") }}
    </div>

    <!-- Add subtask -->
    <form
      v-if="editable"
      class="flex items-center gap-2 mt-1"
      @submit.prevent="createSubtask"
    >
      <input
        v-model="newSubject"
        type="text"
        :placeholder="__('Add a subtask…')"
        class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
        maxlength="500"
      />
      <Button
        :label="__('Add')"
        theme="blue"
        variant="solid"
        size="sm"
        :loading="addRes.loading"
        @click="createSubtask"
      />
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Avatar,
  Button,
  createListResource,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { __ } from "@/translation";
import { useAuthStore } from "@/stores/auth";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideClock from "~icons/lucide/clock";
import LucideListTodo from "~icons/lucide/list-todo";
import LucideCircle from "~icons/lucide/circle";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideCalendarClock from "~icons/lucide/calendar-clock";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideStar from "~icons/lucide/star";
import LucideX from "~icons/lucide/x";

interface P {
  taskId: string;
  editable?: boolean;
  estimatedHours?: number;
}
const props = withDefaults(defineProps<P>(), { editable: false, estimatedHours: 0 });

const overBudget = computed(
  () => props.estimatedHours > 0 && summary.value.hours_spent > props.estimatedHours
);

const authStore = useAuthStore();
const { userId } = authStore;

const newSubject = ref("");

const subtasks = createResource({
  url: "helpdesk.api.task_subtask.get_subtasks",
  makeParams: () => ({ task: props.taskId }),
  auto: !!props.taskId,
  onError: (e: any) => console.warn("[helpdesk] task subtasks:", e),
});
const summaryRes = createResource({
  url: "helpdesk.api.task_subtask.get_summary",
  makeParams: () => ({ task: props.taskId }),
  auto: !!props.taskId,
  onError: (e: any) => console.warn("[helpdesk] task subtask summary:", e),
});
const summary = computed(
  () =>
    summaryRes.data || {
      total: 0,
      done: 0,
      in_progress: 0,
      todo: 0,
      overdue: 0,
      progress: 0,
      hours_spent: 0,
      avg_score: 0,
    }
);

function pct(count: number) {
  const total = summary.value.total || 0;
  return total ? `${Math.round((count / total) * 100)}%` : "0%";
}

interface SubtaskRow {
  name?: string;
  subject?: string;
  status: string;
  due_date?: string | null;
  reviewer?: string | null;
  score?: number;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  // Who does the work: "Us" | "Client" | "Joint". Absent on customer payloads.
  responsibility?: string | null;
  // Rows come straight off the API, so patchSubtask() can read/write any field.
  [key: string]: any;
}
function isOverdue(t: SubtaskRow) {
  if (!t.due_date || t.status === "Done") return false;
  return dayjs(t.due_date).isBefore(dayjs().startOf("day"));
}
function canScore(t: SubtaskRow) {
  return !!authStore.isManager || (!!t.reviewer && t.reviewer === userId);
}

const agents = createListResource({
  doctype: "HD Agent",
  fields: ["name", "agent_name"],
  filters: { is_active: 1 },
  pageLength: 500,
  auto: props.editable,
});
const agentOptions = computed(() =>
  (agents.data || []).map((a: any) => ({
    value: a.name,
    label: a.agent_name || a.name,
  }))
);

// --- responsibility: who does the work (us, the client, or both) ---
// Not the same thing as customer visibility (`customer_visible`), which decides
// who may *see* the subtask. Stored values, in the doctype's order.
const RESPONSIBILITIES = ["Us", "Client", "Joint"] as const;
/** Shown as stored — "Us" / "Client" / "Joint" — translated where we have one. */
function respLabel(r: string | null | undefined) {
  return r ? __(r) : "";
}
function respClass(r: string | null | undefined) {
  return (
    {
      Us: "bg-blue-100 text-blue-700",
      Client: "bg-amber-100 text-amber-700",
      Joint: "bg-violet-100 text-violet-700",
    }[r || ""] || "bg-surface-gray-2 text-ink-gray-6"
  );
}

// --- filters (view-only) ---
// These narrow the rows on screen and nothing else: no save is triggered, and
// the done chip, progress bar and hours rollup keep counting every subtask.
// A short list isn't worth a toolbar, so the filters only appear once there are
// enough rows to be worth narrowing.
const FILTER_THRESHOLD = 4;
const statusFilter = ref("");
const assigneeFilter = ref(""); // "" all · "__unassigned__" · else assigned_to
const responsibilityFilter = ref(""); // "" all · "Us" | "Client" | "Joint"

const rows = computed<SubtaskRow[]>(() => subtasks.data || []);
// Agents only: a customer's rows are scrubbed of assignee and responsibility,
// so there would be nothing to filter by.
const showFilters = computed(
  () => props.editable && rows.value.length >= FILTER_THRESHOLD
);
// Keyed on the field being in the payload at all, not on it being set: rows
// that pre-date the field read as empty, and they still need filtering. A
// payload without the field (a customer's, or an older build) gets no filter.
const hasResponsibility = computed(() =>
  rows.value.some((t) => t.responsibility !== undefined)
);
// Built from the rows themselves, so the list only offers people who appear.
const filterAssigneeOptions = computed(() => {
  const map = new Map<string, string>();
  rows.value.forEach((t) => {
    if (t.assigned_to) map.set(t.assigned_to, t.assigned_to_name || t.assigned_to);
  });
  return Array.from(map, ([value, label]) => ({ value, label }));
});
const hasUnassigned = computed(() => rows.value.some((t) => !t.assigned_to));
const anyFilterActive = computed(
  () => !!statusFilter.value || !!assigneeFilter.value || !!responsibilityFilter.value
);
const visibleSubtasks = computed<SubtaskRow[]>(() => {
  // Filters the user can't see (short list, customer view) never hide a row.
  if (!showFilters.value || !anyFilterActive.value) return rows.value;
  return rows.value.filter((t) => {
    if (statusFilter.value && t.status !== statusFilter.value) return false;
    if (assigneeFilter.value === "__unassigned__" && t.assigned_to) return false;
    if (
      assigneeFilter.value &&
      assigneeFilter.value !== "__unassigned__" &&
      t.assigned_to !== assigneeFilter.value
    )
      return false;
    if (
      responsibilityFilter.value &&
      // Blank (pre-backfill) rows read as the stored default, which is what
      // the row's own select shows — filtering "Us" must not hide them.
      (t.responsibility || "Us") !== responsibilityFilter.value
    )
      return false;
    return true;
  });
});
function clearFilters() {
  statusFilter.value = "";
  assigneeFilter.value = "";
  responsibilityFilter.value = "";
}

function reload() {
  subtasks.reload();
  summaryRes.reload();
}
watch(
  () => props.taskId,
  () => {
    // A different task starts unfiltered.
    clearFilters();
    props.taskId && reload();
  }
);
defineExpose({ reload });

const addRes = createResource({
  url: "helpdesk.api.task_subtask.add_subtask",
  onSuccess: () => {
    newSubject.value = "";
    reload();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not add subtask")),
});
function createSubtask() {
  const s = newSubject.value.trim();
  if (!s) return;
  addRes.submit({ task: props.taskId, subject: s });
}

const updateRes = createResource({
  url: "helpdesk.api.task_subtask.update_subtask",
  // Failures are handled per row in patchSubtask() — it reverts the row and
  // toasts there. Without an onError here frappe-ui treats the error as
  // unhandled and runs the app-wide fallback handler too, so one failed save
  // would raise two toasts.
  onError: () => {},
});

// One save at a time per subtask, so two quick edits to the same row (renaming
// it and then flipping its status) can't race each other into a "document has
// been modified" error.
const saveChain: Record<string, Promise<any>> = {};

/**
 * Save one subtask field straight away; revert the row if the server says no.
 * `onRevert` lets a caller put its own uncontrolled input back in step.
 */
function patchSubtask(
  t: SubtaskRow,
  fields: Record<string, any>,
  onRevert?: () => void
) {
  const name = t?.name;
  if (!name) return;
  const previous: Record<string, any> = {};
  const changed: Record<string, any> = {};
  for (const [key, value] of Object.entries(fields)) {
    if ((t[key] ?? "") === (value ?? "")) continue;
    previous[key] = t[key];
    changed[key] = value;
  }
  // Nothing actually changed — don't bother the server.
  if (!Object.keys(changed).length) return;
  // Optimistic: the row shows the edit while the save is in flight.
  Object.assign(t, changed);
  const run: Promise<any> = (saveChain[name] || Promise.resolve())
    .catch(() => {})
    .then(() => updateRes.submit({ name, ...changed }))
    // Roll the progress bar, counts and score rollup forward.
    .then(() => reload())
    .catch((e: any) => {
      Object.assign(t, previous);
      onRevert?.();
      toast.error(e?.messages?.[0] || __("Could not update subtask"));
    })
    .finally(() => {
      if (saveChain[name] === run) delete saveChain[name];
    });
  saveChain[name] = run;
}

/** Rename a subtask from its inline input — fires on blur and on Enter. */
function renameSubtask(t: SubtaskRow, el: HTMLInputElement) {
  const subject = (el.value || "").trim();
  if (!subject || subject === (t.subject || "")) {
    // Blank or unchanged: put the stored subject back in the box, save nothing.
    el.value = t.subject || "";
    return;
  }
  el.value = subject;
  patchSubtask(t, { subject }, () => {
    el.value = t.subject || "";
  });
}

const deleteRes = createResource({
  url: "helpdesk.api.task_subtask.delete_subtask",
  onSuccess: () => reload(),
});
function removeSubtask(name: string) {
  deleteRes.submit({ name });
}

function formatHours(h: number) {
  if (!h) return "0h";
  return Number.isInteger(h) ? `${h}h` : `${h.toFixed(2).replace(/0$/, "")}h`;
}
function statusIcon(status: string) {
  if (status === "Done") return LucideCheckCircle2;
  if (status === "In Progress") return LucideCircleDot;
  return LucideCircle;
}
function statusColor(status: string) {
  if (status === "Done") return "text-green-600";
  if (status === "In Progress") return "text-blue-600";
  return "text-ink-gray-4";
}
</script>
