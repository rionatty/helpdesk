<template>
  <div class="flex flex-col gap-3">
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

    <!-- Subtask list -->
    <div v-if="subtasks.data && subtasks.data.length" class="flex flex-col gap-2">
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
            :class="t.status === 'Done' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
          >
            {{ t.subject }}
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

        <!-- Controls -->
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
            @change="(e) => patchSubtask(t.name, { assigned_to: e.target.value })"
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
            @change="(e) => patchSubtask(t.name, { reviewer: e.target.value })"
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
              @change="(e) => patchSubtask(t.name, { hours_spent: parseFloat(e.target.value) || 0 })"
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
              @change="(e) => patchSubtask(t.name, { due_date: e.target.value })"
            />
          </div>
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
              @click="canScore(t) && patchSubtask(t.name, { score: n === Number(t.score) ? 0 : n })"
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
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

interface P {
  taskId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });

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
  status: string;
  due_date?: string | null;
  reviewer?: string | null;
  score?: number;
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

function reload() {
  subtasks.reload();
  summaryRes.reload();
}
watch(
  () => props.taskId,
  () => props.taskId && reload()
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
  onSuccess: () => reload(),
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not update subtask")),
});
function patchSubtask(name: string, fields: Record<string, any>) {
  updateRes.submit({ name, ...fields });
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
