<template>
  <!-- Customers only see this card when there's something to show. -->
  <div
    v-if="editable || (subtasks.data && subtasks.data.length)"
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

      <!-- Filters (agent only, long lists only). View-only: the counts, the
           progress bar and the estimate above keep covering EVERY subtask —
           only the list below is narrowed. -->
      <div
        v-if="showFilters"
        class="flex flex-wrap items-center gap-2 rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-2.5 py-2"
      >
        <LucideFilter class="size-3.5 text-ink-gray-5 shrink-0" />
        <select
          v-model="rowFilters.status"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          :aria-label="__('Filter by status')"
        >
          <option value="">{{ __("All statuses") }}</option>
          <option value="To Do">{{ __("To Do") }}</option>
          <option value="In Progress">{{ __("In Progress") }}</option>
          <option value="Done">{{ __("Done") }}</option>
        </select>
        <select
          v-model="rowFilters.assignee"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[140px]"
          :aria-label="__('Filter by assignee')"
        >
          <option value="">{{ __("All assignees") }}</option>
          <option
            v-for="a in assigneeFilterOptions"
            :key="a.value"
            :value="a.value"
          >
            {{ a.label }}
          </option>
        </select>
        <select
          v-model="rowFilters.responsibility"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          :aria-label="__('Filter by responsibility')"
        >
          <option value="">{{ __("Everyone") }}</option>
          <option value="Us">{{ __("Us") }}</option>
          <option value="Client">{{ __("Client") }}</option>
          <option value="Joint">{{ __("Joint") }}</option>
        </select>
        <template v-if="filtered">
          <span class="text-xs text-ink-gray-5">
            {{
              __("showing {0} of {1}", [
                visibleSubtasks.length,
                subtasks.data.length,
              ])
            }}
          </span>
          <button
            type="button"
            class="text-xs font-medium text-ink-gray-6 hover:text-ink-gray-8 hover:underline"
            @click="clearFilters"
          >
            {{ __("Clear") }}
          </button>
        </template>
      </div>

      <!-- Subtask list -->
      <div v-if="visibleSubtasks.length" class="flex flex-col gap-2">
        <div
          v-for="t in visibleSubtasks"
          :key="t.name"
          class="rounded-lg border border-l-4 px-3 py-2.5 flex flex-col gap-2 transition-colors"
          :class="rowTone(t.status)"
        >
          <div class="flex items-start gap-2">
            <component
              :is="statusIcon(t.status)"
              class="size-4 mt-0.5 shrink-0"
              :class="statusColor(t.status)"
            />
            <!-- Agents rename in place; customers keep the plain-text view. -->
            <input
              v-if="editable"
              type="text"
              :value="t.subject"
              maxlength="500"
              :aria-label="__('Subtask subject')"
              class="text-sm flex-1 min-w-0 leading-snug font-medium bg-transparent rounded-md border border-transparent px-1.5 py-0.5 hover:border-outline-gray-2 focus:border-blue-400 focus:bg-surface-white focus:outline-none"
              :class="
                t.status === 'Done'
                  ? 'text-ink-gray-5 line-through'
                  : 'text-ink-gray-8'
              "
              @blur="(e) => renameSubtask(t, e.target)"
              @keyup.enter="(e) => e.target.blur()"
            />
            <span
              v-else
              class="text-sm flex-1 leading-snug font-medium"
              :class="
                t.status === 'Done'
                  ? 'text-ink-gray-5 line-through'
                  : 'text-ink-gray-8'
              "
            >
              {{ t.subject }}
            </span>
            <!-- Who does the work. Internal: agents only, and hidden when the
                 field isn't there (older rows / API without it). -->
            <span
              v-if="editable && responsibilityOf(t)"
              class="shrink-0 text-[10px] font-medium rounded-full px-1.5 py-0.5"
              :class="responsibilityClass(responsibilityOf(t))"
              :title="__('Who does this work')"
            >
              {{ __(responsibilityOf(t)) }}
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
              class="text-ink-gray-4 hover:text-ink-gray-8 shrink-0"
              :aria-label="__('Edit subtask: {0}', [t.subject])"
              :title="__('Edit subtask')"
              @click="openEditor(t)"
            >
              <LucidePencil class="size-3.5" />
            </button>
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

          <p
            v-if="t.description"
            class="ps-6 text-xs text-ink-gray-6 whitespace-pre-line leading-relaxed"
          >
            {{ t.description }}
          </p>

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
            <select
              :value="responsibilityOf(t) || 'Us'"
              class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              :aria-label="__('Responsibility')"
              :title="__('Who does this work')"
              @change="
                (e) => patchSubtask(t.name, { responsibility: e.target.value })
              "
            >
              <option value="Us">{{ __("Us") }}</option>
              <option value="Client">{{ __("Client") }}</option>
              <option value="Joint">{{ __("Joint") }}</option>
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
            <!-- Review: who checks this, and where it stands -->
            <div class="flex items-center gap-1.5">
              <Badge
                v-if="t.review_status"
                :label="
                  t.review_status === 'Reviewed'
                    ? __('Reviewed')
                    : __('Pending review')
                "
                :theme="t.review_status === 'Reviewed' ? 'green' : 'orange'"
                variant="subtle"
              />
              <button
                v-if="canMarkReviewed(t)"
                type="button"
                class="text-xs font-medium text-green-700 hover:underline"
                @click="markReviewed(t)"
              >
                {{ __("Mark reviewed") }}
              </button>
              <button
                v-if="t.review_status !== 'Reviewed'"
                type="button"
                class="text-xs font-medium text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
                @click="openReview(t)"
              >
                {{
                  t.review_status === "Pending Review"
                    ? __("Remind reviewer")
                    : __("Request review")
                }}
              </button>
              <span
                v-if="t.reviewer_name"
                class="text-[11px] text-ink-gray-5 truncate max-w-[110px]"
                :title="__('Reviewer: {0}', [t.reviewer_name])"
              >
                {{ t.reviewer_name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters hid everything — the list itself isn't empty. -->
      <div
        v-else-if="subtasks.data && subtasks.data.length"
        class="flex flex-wrap items-center gap-2 text-xs text-ink-gray-5 px-1 py-1"
      >
        {{ __("No subtasks match these filters.") }}
        <button
          type="button"
          class="font-medium text-ink-gray-7 hover:text-ink-gray-9 hover:underline"
          @click="clearFilters"
        >
          {{ __("Clear filters") }}
        </button>
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
    <!-- Full editor. The row keeps its quick controls for triage; the long
         fields live here: a 500-character subject reads badly in a one-line
         input, and the description has no inline home at all. -->
    <Dialog
      v-if="editable"
      v-model="showEditor"
      :options="{ title: __('Edit subtask'), size: 'lg' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <div class="flex flex-col gap-1">
            <FormControl
              v-model="editForm.subject"
              type="textarea"
              :label="__('Subject')"
              :rows="2"
              maxlength="500"
            />
            <span
              class="self-end text-[11px]"
              :class="subjectTooLong ? 'text-ink-red-3' : 'text-ink-gray-4'"
            >
              {{ subjectLength }}/500
            </span>
          </div>
          <FormControl
            v-model="editForm.description"
            type="textarea"
            :label="__('Description')"
            :rows="4"
            :placeholder="__('Details, acceptance criteria, notes')"
          />
          <div class="grid grid-cols-2 gap-3">
            <FormControl
              v-model="editForm.status"
              type="select"
              :label="__('Status')"
              :options="statusSelectOptions"
            />
            <FormControl
              v-model="editForm.responsibility"
              type="select"
              :label="__('Responsibility')"
              :options="respSelectOptions"
            />
            <FormControl
              v-model="editForm.assigned_to"
              type="select"
              :label="__('Assignee')"
              :options="assigneeSelectOptions"
            />
            <FormControl
              v-model="editForm.reviewer"
              type="select"
              :label="__('Reviewer')"
              :options="reviewerSelectOptions"
            />
            <FormControl
              v-model="editForm.hours_spent"
              type="number"
              :label="__('Hours spent')"
            />
            <FormControl
              v-model="editForm.due_date"
              type="date"
              :label="__('Due date')"
            />
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-2 w-full">
          <Button :label="__('Cancel')" @click="showEditor = false" />
          <Button
            class="flex-1"
            variant="solid"
            :label="__('Save')"
            :disabled="subjectTooLong"
            @click="saveEditor"
          />
        </div>
      </template>
    </Dialog>
    <!-- Ask a colleague to check a subtask. The reviewer is picked here, so
         the button works even on a subtask that has none set yet. -->
    <Dialog
      v-if="editable"
      v-model="showReviewDialog"
      :options="{ title: __('Request review'), size: 'sm' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3">
          <p class="text-sm font-medium text-ink-gray-8">
            {{ reviewingSubtask?.subject }}
          </p>
          <FormControl
            v-model="reviewPick"
            type="select"
            :label="__('Reviewer')"
            :options="reviewerPickOptions"
          />
          <p class="text-xs text-ink-gray-5">
            {{
              __(
                "They get a notification and an email with a link to this ticket."
              )
            }}
          </p>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-2 w-full">
          <Button :label="__('Cancel')" @click="showReviewDialog = false" />
          <Button
            class="flex-1"
            variant="solid"
            theme="blue"
            :label="__('Send request')"
            :loading="requestReviewRes.loading"
            :disabled="!reviewPick"
            @click="sendReviewRequest"
          />
        </div>
      </template>
    </Dialog>
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
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucidePencil from "~icons/lucide/pencil";
import LucideClock from "~icons/lucide/clock";
import LucideTarget from "~icons/lucide/target";
import LucideListTodo from "~icons/lucide/list-todo";
import LucideCircle from "~icons/lucide/circle";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideCalendarClock from "~icons/lucide/calendar-clock";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideFilter from "~icons/lucide/filter";

interface P {
  ticketId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });
// Hours changed: the support-hours panel next to this one refreshes.
const emit = defineEmits<{ (e: "changed"): void }>();

// Signing off a review is restricted to the agent who was asked (or a manager).
const { userId, isManager } = useAuthStore();

const newSubject = ref("");

const subtasks = createResource({
  url: "helpdesk.api.subtask.get_subtasks",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
  // Auxiliary widget — degrade silently rather than toasting at the viewer.
  onError: (e: any) => console.warn("[helpdesk] subtasks:", e),
});

const summaryRes = createResource({
  url: "helpdesk.api.subtask.get_summary",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
  onError: (e: any) => console.warn("[helpdesk] subtask summary:", e),
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

// Who does the work: us (CyveTech), the client, or both together. Internal —
// kept out of the customer view. Independent of customer visibility.
const RESPONSIBILITIES = ["Us", "Client", "Joint"];
/** The row's stored responsibility, or "" when it isn't set / isn't there. */
function responsibilityOf(t: any): string {
  const value = t?.responsibility;
  return RESPONSIBILITIES.includes(value) ? value : "";
}
function responsibilityClass(value: string) {
  if (value === "Client") return "bg-amber-100 text-amber-700";
  if (value === "Joint") return "bg-violet-100 text-violet-700";
  return "bg-blue-100 text-blue-700";
}

// --- Filters -------------------------------------------------------------
// View-only: they narrow the rendered list and nothing else. The summary,
// progress bar, overdue count and the estimate all come from get_summary,
// which always covers every subtask of the ticket.
//
// Only worth the space once scanning the list is actually work.
const FILTER_THRESHOLD = 5;
// "" means "all"; a filter on the assignee needs its own sentinel for "nobody".
const UNASSIGNED = "__unassigned__";
const rowFilters = ref({ status: "", assignee: "", responsibility: "" });

// Agent-only, like the per-row controls: the customer view has no assignee or
// responsibility to filter on in the first place.
const showFilters = computed(
  () => props.editable && (subtasks.data?.length || 0) >= FILTER_THRESHOLD
);
const filtered = computed(
  () =>
    showFilters.value &&
    !!(
      rowFilters.value.status ||
      rowFilters.value.assignee ||
      rowFilters.value.responsibility
    )
);
const visibleSubtasks = computed(() => {
  const rows = subtasks.data || [];
  // Filters that aren't on screen must not quietly hide rows.
  if (!filtered.value) return rows;
  const f = rowFilters.value;
  return rows.filter((t: any) => {
    if (f.status && t.status !== f.status) return false;
    if (f.assignee && (t.assigned_to || UNASSIGNED) !== f.assignee)
      return false;
    // A blank/legacy value reads as the stored default "Us" here (the row's
    // own select shows "Us" for it), even though the badge stays hidden.
    if (f.responsibility && (responsibilityOf(t) || "Us") !== f.responsibility)
      return false;
    return true;
  });
});
// Only the people who actually appear in this ticket's subtasks.
const assigneeFilterOptions = computed(() => {
  const rows = subtasks.data || [];
  const seen = new Map<string, string>();
  let anyUnassigned = false;
  for (const t of rows as any[]) {
    if (!t.assigned_to) {
      anyUnassigned = true;
      continue;
    }
    if (!seen.has(t.assigned_to))
      seen.set(t.assigned_to, t.assigned_to_name || t.assigned_to);
  }
  const options = [...seen.entries()]
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
  if (anyUnassigned)
    options.push({ value: UNASSIGNED, label: __("Unassigned") });
  return options;
});
function clearFilters() {
  rowFilters.value = { status: "", assignee: "", responsibility: "" };
}

const overBudget = computed(
  () =>
    summary.value.estimated_hours > 0 &&
    summary.value.hours_spent > summary.value.estimated_hours
);

function reload() {
  subtasks.reload();
  summaryRes.reload();
}
defineExpose({ reload });

watch(
  () => props.ticketId,
  () => {
    // A filter from the previous ticket means nothing on this one.
    clearFilters();
    reload();
  }
);

const addRes = createResource({
  url: "helpdesk.api.subtask.add_subtask",
  onSuccess: () => {
    newSubject.value = "";
    // A new subtask starts as "To Do" / "Us" / unassigned, which an active
    // filter could hide — so the agent would see nothing happen. Show it.
    clearFilters();
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
  onSuccess: () => {
    reload();
    emit("changed");
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update subtask")),
});
function patchSubtask(name: string, fields: Record<string, any>) {
  updateRes.submit({ name, ...fields });
}

// Renames revert the row and toast themselves (see renameSubtask), so this
// resource must not toast as well: frappe-ui falls back to the app-wide error
// handler when a resource has no onError, and the user would get two toasts.
const subjectRes = createResource({
  url: "helpdesk.api.subtask.update_subtask",
  onError: () => {},
});
/** Save an edited subject; put the stored one back if the server says no. */
function renameSubtask(t: any, el: HTMLInputElement) {
  const subject = (el.value || "").trim();
  if (!subject || subject === t.subject) {
    // Blank or unchanged: restore the stored subject, nothing to save.
    el.value = t.subject || "";
    return;
  }
  const previous = t.subject;
  // Optimistic: the row shows the new subject while the save is in flight.
  // No reload() on success — nothing in the summary depends on the subject,
  // and a refetch here could clobber another row's in-flight edit.
  t.subject = subject;
  subjectRes.submit({ name: t.name, subject }).catch((e: any) => {
    t.subject = previous;
    el.value = previous || "";
    toast.error(e?.messages?.[0] || __("Could not rename subtask"));
  });
}

const deleteRes = createResource({
  url: "helpdesk.api.subtask.delete_subtask",
  onSuccess: () => {
    reload();
    emit("changed");
  },
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

// Whole-row status colour, same palette as the task board.
function rowTone(status: string) {
  return (
    {
      "In Progress": "bg-blue-50 border-blue-100 border-l-blue-400",
      Done: "bg-green-50 border-green-100 border-l-green-500",
    }[status] || "bg-surface-gray-1 border-outline-gray-1 border-l-outline-gray-3"
  );
}

// --- Full edit dialog -------------------------------------------------------
const editingSubtask = ref<any>(null);
const editForm = ref<Record<string, any>>({});
const showEditor = computed({
  get: () => !!editingSubtask.value,
  set: (open: boolean) => {
    if (!open) editingSubtask.value = null;
  },
});
const subjectLength = computed(() => (editForm.value.subject || "").length);
const subjectTooLong = computed(() => subjectLength.value > 500);
const statusSelectOptions = ["To Do", "In Progress", "Done"].map((s) => ({
  label: __(s),
  value: s,
}));
const respSelectOptions = RESPONSIBILITIES.map((r) => ({ label: __(r), value: r }));
const assigneeSelectOptions = computed(() => [
  { label: __("Unassigned"), value: "" },
  ...agentOptions.value,
]);
const reviewerSelectOptions = computed(() => [
  { label: __("No reviewer"), value: "" },
  ...agentOptions.value,
]);

// --- Review ----------------------------------------------------------------
// An agent asks a colleague to check a subtask; the colleague signs it off.
// Internal to the team — the customer view never renders any of it.
const reviewerPickOptions = computed(() => [
  { label: __("Choose an agent"), value: "" },
  ...agentOptions.value,
]);
const reviewingSubtask = ref<any>(null);
const reviewPick = ref("");
const showReviewDialog = computed({
  get: () => !!reviewingSubtask.value,
  set: (open: boolean) => {
    if (!open) reviewingSubtask.value = null;
  },
});

function openReview(t: any) {
  // Default to whoever already reviews it, so "Remind reviewer" is one click.
  reviewPick.value = t.reviewer || "";
  reviewingSubtask.value = t;
}

const requestReviewRes = createResource({
  url: "helpdesk.api.subtask.request_review",
  onSuccess: () => {
    reviewingSubtask.value = null;
    toast.success(__("Reviewer notified"));
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not request review")),
});
function sendReviewRequest() {
  const t = reviewingSubtask.value;
  if (!t || !reviewPick.value) return;
  requestReviewRes.submit({ name: t.name, reviewer: reviewPick.value });
}

const markReviewedRes = createResource({
  url: "helpdesk.api.subtask.mark_reviewed",
  onSuccess: () => {
    toast.success(__("Marked as reviewed"));
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not mark this reviewed")),
});
/** Only the agent who was asked (or a manager) signs a review off. */
function canMarkReviewed(t: any) {
  return (
    t.review_status === "Pending Review" &&
    (!!isManager || (!!t.reviewer && t.reviewer === userId))
  );
}
function markReviewed(t: any) {
  markReviewedRes.submit({ name: t.name });
}

function openEditor(t: any) {
  editForm.value = {
    subject: t.subject || "",
    description: t.description || "",
    status: t.status || "To Do",
    responsibility: responsibilityOf(t) || "Us",
    assigned_to: t.assigned_to || "",
    reviewer: t.reviewer || "",
    hours_spent: Number(t.hours_spent) || 0,
    due_date: t.due_date || "",
  };
  editingSubtask.value = t;
}

function saveEditor() {
  const t = editingSubtask.value;
  if (!t) return;
  const f = editForm.value;
  const subject = (f.subject || "").trim();
  if (!subject) {
    toast.error(__("Subject is required"));
    return;
  }
  if (subject.length > 500) {
    toast.error(__("A subject can be at most {0} characters", [500]));
    return;
  }
  const next: Record<string, any> = {
    subject,
    description: f.description || "",
    status: f.status,
    responsibility: f.responsibility,
    assigned_to: f.assigned_to || "",
    reviewer: f.reviewer || "",
    hours_spent: Math.max(0, parseFloat(f.hours_spent) || 0),
    due_date: f.due_date || "",
  };
  // Send only what changed; updateRes reloads on success, toasts on error.
  const changed: Record<string, any> = {};
  for (const [key, value] of Object.entries(next)) {
    if ((t[key] ?? "") !== (value ?? "")) changed[key] = value;
  }
  editingSubtask.value = null;
  if (Object.keys(changed).length) updateRes.submit({ name: t.name, ...changed });
}
function statusTheme(status: string) {
  if (status === "Done") return "green";
  if (status === "In Progress") return "blue";
  return "gray";
}
</script>
