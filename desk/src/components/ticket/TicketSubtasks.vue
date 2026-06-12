<template>
  <div
    class="rounded-xl border border-outline-gray-2 bg-surface-white shadow-sm overflow-hidden"
  >
    <!-- Standout header -->
    <div
      class="flex items-center justify-between gap-2 px-4 py-3 bg-gradient-to-r from-violet-100 to-blue-100 border-b border-outline-gray-2"
    >
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center shadow-sm ring-1 ring-inset ring-white/40"
        >
          <LucideListTodo class="size-4 text-white" />
        </div>
        <span class="text-sm font-bold text-ink-gray-9">
          {{ __("Subtasks") }}
        </span>
      </div>
      <span
        v-if="summary.total"
        class="text-xs font-semibold text-violet-700 bg-violet-200/70 rounded-full px-2 py-0.5"
      >
        {{ summary.done }}/{{ summary.total }} {{ __("done") }}
      </span>
    </div>

    <div class="p-4 flex flex-col gap-3">
      <!-- Progress bar — segmented by status, animated -->
      <div v-if="summary.total" class="flex flex-col gap-1.5">
        <div
          class="flex h-2.5 w-full rounded-full bg-surface-gray-2 overflow-hidden"
        >
          <div
            class="h-full bg-gradient-to-r from-violet-500 to-blue-500 transition-[width] duration-500 ease-out"
            :style="{ width: pct(summary.done) }"
          />
          <div
            class="h-full bg-blue-300 transition-[width] duration-500 ease-out"
            :style="{ width: pct(summary.in_progress) }"
          />
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="font-medium text-ink-gray-7">
            {{ summary.progress }}% {{ __("complete") }}
          </span>
          <div class="flex items-center gap-2.5">
            <span
              v-if="summary.overdue"
              class="inline-flex items-center gap-1 text-ink-red-3 font-medium"
            >
              <LucideAlertTriangle class="size-3" />
              {{ summary.overdue }} {{ __("overdue") }}
            </span>
            <span v-if="editable && summary.hours_spent" class="text-ink-gray-6">
              {{ formatHours(summary.hours_spent) }} {{ __("logged") }}
            </span>
          </div>
        </div>
        <!-- Legend -->
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-gray-5">
          <span class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-violet-500" />
            {{ summary.done }} {{ __("done") }}
          </span>
          <span v-if="summary.in_progress" class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-blue-300" />
            {{ summary.in_progress }} {{ __("in progress") }}
          </span>
          <span v-if="summary.todo" class="flex items-center gap-1">
            <span class="size-2 rounded-full bg-surface-gray-4" />
            {{ summary.todo }} {{ __("to do") }}
          </span>
        </div>
      </div>

      <!-- Subtask list -->
      <div
        v-if="subtasks.data && subtasks.data.length"
        class="flex flex-col gap-2"
      >
        <div
          v-for="t in subtasks.data"
          :key="t.name"
          class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5 flex flex-col gap-2"
        >
          <div class="flex items-start gap-2">
            <component
              :is="statusIcon(t.status)"
              class="size-4 mt-0.5 shrink-0"
              :class="statusColor(t.status)"
            />
            <span
              class="text-sm flex-1 leading-snug font-medium"
              :class="
                t.status === 'Done'
                  ? 'text-ink-gray-5 line-through'
                  : 'text-ink-gray-8'
              "
            >
              {{ t.subject }}
            </span>
            <Badge
              v-if="!editable"
              :label="__(t.status)"
              :theme="statusTheme(t.status)"
              variant="subtle"
            />
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

          <!-- Read-only assignee + due date line -->
          <div
            v-if="!editable && (t.assigned_to_name || t.due_date)"
            class="flex flex-wrap items-center gap-x-3 gap-y-1 ps-6 text-xs"
          >
            <span
              v-if="t.assigned_to_name"
              class="flex items-center gap-1.5 text-ink-gray-6"
            >
              <Avatar size="xs" :label="t.assigned_to_name" />
              {{ t.assigned_to_name }}
            </span>
            <span
              v-if="t.due_date"
              class="flex items-center gap-1"
              :class="isOverdue(t) ? 'text-ink-red-3 font-medium' : 'text-ink-gray-6'"
            >
              <LucideCalendarClock class="size-3.5" />
              {{ dueLabel(t) }}
            </span>
          </div>

          <!-- Agent controls -->
          <div v-if="editable" class="flex flex-wrap items-center gap-2 ps-6">
            <select
              :value="t.status"
              class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              @change="(e) => patchSubtask(t.name, { status: e.target.value })"
            >
              <option value="To Do">{{ __("To Do") }}</option>
              <option value="In Progress">{{ __("In Progress") }}</option>
              <option value="Done">{{ __("Done") }}</option>
            </select>
            <select
              :value="t.assigned_to || ''"
              class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[120px]"
              :aria-label="__('Assignee')"
              @change="
                (e) => patchSubtask(t.name, { assigned_to: e.target.value })
              "
            >
              <option value="">{{ __("Unassigned") }}</option>
              <option
                v-for="a in agentOptions"
                :key="a.value"
                :value="a.value"
              >
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
                @change="
                  (e) =>
                    patchSubtask(t.name, {
                      hours_spent: parseFloat(e.target.value) || 0,
                    })
                "
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
                :class="
                  isOverdue(t)
                    ? 'border-red-300 text-ink-red-3'
                    : 'border-outline-gray-2 text-ink-gray-7'
                "
                :aria-label="__('Due date')"
                @change="(e) => patchSubtask(t.name, { due_date: e.target.value })"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!subtasks.loading"
        class="text-xs text-ink-gray-5 px-1 py-1"
      >
        {{
          editable
            ? __("No subtasks yet — break this ticket into steps below.")
            : __("No subtasks have been added yet.")
        }}
      </div>

      <!-- Add subtask (agent only) -->
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
          maxlength="200"
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

      <!-- Estimate (agent only) -->
      <div
        v-if="editable"
        class="flex items-center gap-2 mt-1 pt-3 border-t border-outline-gray-1"
      >
        <LucideTarget class="size-4 text-ink-gray-5 shrink-0" />
        <span class="text-sm text-ink-gray-6 flex-1">{{ __("Estimated") }}</span>
        <input
          type="number"
          min="0"
          step="0.5"
          :value="summary.estimated_hours"
          class="w-20 text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-8 focus:outline-none focus:border-blue-400"
          :aria-label="__('Estimated hours')"
          @change="(e) => saveEstimate(parseFloat(e.target.value) || 0)"
        />
        <span class="text-sm text-ink-gray-5">{{ __("hrs") }}</span>
      </div>
      <!-- Time summary (agent only) -->
      <div
        v-if="editable && (summary.estimated_hours || summary.hours_spent)"
        class="flex items-center justify-between text-xs px-1"
        :class="overBudget ? 'text-ink-red-3 font-medium' : 'text-ink-gray-6'"
      >
        <span>
          {{ formatHours(summary.hours_spent) }} {{ __("spent") }}
          <template v-if="summary.estimated_hours">
            / {{ formatHours(summary.estimated_hours) }} {{ __("estimated") }}
          </template>
        </span>
        <span v-if="overBudget">{{ __("over budget") }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Avatar,
  Badge,
  Button,
  createListResource,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { __ } from "@/translation";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideClock from "~icons/lucide/clock";
import LucideTarget from "~icons/lucide/target";
import LucideListTodo from "~icons/lucide/list-todo";
import LucideCircle from "~icons/lucide/circle";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideCalendarClock from "~icons/lucide/calendar-clock";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";

interface P {
  ticketId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });

const newSubject = ref("");

const subtasks = createResource({
  url: "helpdesk.api.subtask.get_subtasks",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
});

const summaryRes = createResource({
  url: "helpdesk.api.subtask.get_summary",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
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
      estimated_hours: 0,
    }
);

// % of the bar a given status count should occupy.
function pct(count: number) {
  const total = summary.value.total || 0;
  return total ? `${Math.round((count / total) * 100)}%` : "0%";
}

interface SubtaskRow {
  status: string;
  due_date?: string | null;
}
function isOverdue(t: SubtaskRow) {
  if (!t.due_date || t.status === "Done") return false;
  return dayjs(t.due_date).isBefore(dayjs().startOf("day"));
}
function dueLabel(t: SubtaskRow) {
  const date = dayjs(t.due_date).format("MMM D");
  return isOverdue(t) ? __("Overdue · {0}", [date]) : __("Due {0}", [date]);
}

// Agents for the assignee picker — only fetched in the agent (editable)
// context, since customers don't have read access to HD Agent.
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

const overBudget = computed(
  () =>
    summary.value.estimated_hours > 0 &&
    summary.value.hours_spent > summary.value.estimated_hours
);

function reload() {
  subtasks.reload();
  summaryRes.reload();
}

watch(
  () => props.ticketId,
  () => reload()
);

const addRes = createResource({
  url: "helpdesk.api.subtask.add_subtask",
  onSuccess: () => {
    newSubject.value = "";
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not add subtask")),
});
function createSubtask() {
  const s = newSubject.value.trim();
  if (!s) return;
  addRes.submit({ ticket: props.ticketId, subject: s });
}

const updateRes = createResource({
  url: "helpdesk.api.subtask.update_subtask",
  onSuccess: () => reload(),
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update subtask")),
});
function patchSubtask(name: string, fields: Record<string, any>) {
  updateRes.submit({ name, ...fields });
}

const deleteRes = createResource({
  url: "helpdesk.api.subtask.delete_subtask",
  onSuccess: () => reload(),
});
function removeSubtask(name: string) {
  deleteRes.submit({ name });
}

const estimateRes = createResource({
  url: "helpdesk.api.subtask.set_estimate",
  onSuccess: () => summaryRes.reload(),
});
function saveEstimate(hours: number) {
  estimateRes.submit({ ticket: props.ticketId, hours });
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
function statusTheme(status: string) {
  if (status === "Done") return "green";
  if (status === "In Progress") return "blue";
  return "gray";
}
</script>
