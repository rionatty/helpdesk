<template>
  <div class="flex flex-col gap-3">
    <!-- Section header -->
    <div class="flex items-center justify-between gap-2">
      <div
        class="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-violet-700"
      >
        <span class="h-3 w-1 rounded-full bg-violet-500" />
        {{ __("Subtasks") }}
      </div>
      <span v-if="summary.total" class="text-xs text-ink-gray-5">
        {{ summary.done }}/{{ summary.total }} {{ __("done") }}
      </span>
    </div>

    <!-- Progress bar -->
    <div v-if="summary.total" class="flex flex-col gap-1">
      <div class="h-2 w-full rounded-full bg-surface-gray-3 overflow-hidden">
        <div
          class="h-full rounded-full bg-gradient-to-r from-violet-500 to-blue-500 transition-all"
          :style="{ width: summary.progress + '%' }"
        />
      </div>
      <div class="flex items-center justify-between text-xs text-ink-gray-5">
        <span>{{ summary.progress }}% {{ __("complete") }}</span>
        <span v-if="editable && summary.hours_spent">
          {{ formatHours(summary.hours_spent) }} {{ __("logged") }}
        </span>
      </div>
    </div>

    <!-- Subtask list -->
    <div v-if="subtasks.data && subtasks.data.length" class="flex flex-col gap-1.5">
      <div
        v-for="t in subtasks.data"
        :key="t.name"
        class="rounded-lg border border-outline-gray-1 px-3 py-2 flex flex-col gap-2"
      >
        <div class="flex items-start gap-2">
          <component
            :is="statusIcon(t.status)"
            class="size-4 mt-0.5 shrink-0"
            :class="statusColor(t.status)"
          />
          <span
            class="text-sm flex-1 leading-snug"
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
        <!-- Agent controls -->
        <div v-if="editable" class="flex items-center gap-2 ps-6">
          <select
            :value="t.status"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            @change="
              (e) => patchSubtask(t.name, { status: e.target.value })
            "
          >
            <option value="To Do">{{ __("To Do") }}</option>
            <option value="In Progress">{{ __("In Progress") }}</option>
            <option value="Done">{{ __("Done") }}</option>
          </select>
          <div class="flex items-center gap-1">
            <LucideClock class="size-3.5 text-ink-gray-5" />
            <input
              type="number"
              min="0"
              step="0.25"
              :value="t.hours_spent"
              class="w-16 text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
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
        variant="subtle"
        size="sm"
        :loading="addRes.loading"
        @click="createSubtask"
      />
    </form>

    <!-- Estimate (agent only) -->
    <div
      v-if="editable"
      class="flex items-center gap-2 mt-2 pt-2 border-t border-outline-gray-1"
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
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Badge, Button, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideClock from "~icons/lucide/clock";
import LucideTarget from "~icons/lucide/target";
import LucideCircle from "~icons/lucide/circle";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";

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
      progress: 0,
      hours_spent: 0,
      estimated_hours: 0,
    }
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
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not add subtask")),
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
