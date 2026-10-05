<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center"
        >
          <LucideFlag class="size-4" />
        </div>
        <span class="text-sm font-semibold text-ink-gray-8">
          {{ __("Milestones") }}
        </span>
        <span v-if="milestones.data?.length" class="text-xs text-ink-gray-5">
          · {{ milestones.data.length }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="milestones.data?.length"
          type="button"
          class="text-xs font-medium text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
          @click="toggleAll"
        >
          {{ allCollapsed ? __("Expand all") : __("Collapse all") }}
        </button>
        <Button
          v-if="editable"
          variant="subtle"
          size="sm"
          @click="openCreate"
        >
          <template #prefix><LucidePlus class="size-3.5" /></template>
          {{ __("Add milestone") }}
        </Button>
      </div>
    </div>

    <!-- Who does the work: implementor / client split. Agents only. -->
    <div
      v-if="editable && anyTasks"
      class="flex flex-wrap items-center gap-1 -mt-1"
    >
      <span class="text-[11px] text-ink-gray-5 me-0.5">
        {{ __("Responsibility") }}
      </span>
      <button
        v-for="o in respFilterOptions"
        :key="o.value"
        type="button"
        class="text-[11px] rounded-full border px-2 py-0.5 transition-colors"
        :class="
          respFilter === o.value
            ? respChipActiveClass(o.value)
            : 'border-transparent text-ink-gray-6 hover:bg-surface-gray-2'
        "
        :aria-pressed="respFilter === o.value"
        @click="respFilter = o.value"
      >
        {{ o.label }}
      </button>
    </div>

    <!-- Tracker -->
    <div
      v-if="milestones.data?.length"
      class="flex flex-col"
    >
      <div
        v-for="(m, i) in milestones.data"
        :key="m.name"
        class="flex gap-3"
      >
        <!-- Rail (each milestone has its own colour) -->
        <div class="flex flex-col items-center w-5 shrink-0">
          <span
            class="size-4 rounded-full shrink-0 mt-1.5 flex items-center justify-center ring-2 ring-inset ring-white/50 shadow-sm"
            :style="{ backgroundColor: mColor(m.name).dot }"
          >
            <LucideCheck
              v-if="m.status === 'Completed'"
              class="size-2.5 text-white"
            />
          </span>
          <span
            v-if="i < milestones.data.length - 1"
            class="w-0.5 flex-1 my-0.5 rounded-full"
            :style="{ backgroundColor: mColor(m.name).dot, opacity: 0.35 }"
          />
        </div>

        <!-- Body -->
        <div class="flex-1 flex flex-col min-w-0 mb-2">
        <button
          type="button"
          class="text-start rounded-lg border-l-[3px] px-3 py-2 -mt-0.5 transition-colors"
          :class="editable ? 'hover:bg-surface-menu-bar' : 'cursor-default'"
          :style="{ borderLeftColor: mColor(m.name).dot }"
          @click="editable && openEdit(m)"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span
              role="button"
              tabindex="0"
              class="-ms-1 shrink-0 rounded p-0.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8"
              :aria-expanded="!isCollapsed(m.name)"
              :title="isCollapsed(m.name) ? __('Show details') : __('Hide details')"
              @click.stop="toggle(m.name)"
              @keydown.enter.stop.prevent="toggle(m.name)"
              @keydown.space.stop.prevent="toggle(m.name)"
            >
              <LucideChevronRight
                class="size-4 transition-transform"
                :class="isCollapsed(m.name) ? '' : 'rotate-90'"
              />
            </span>
            <span class="text-sm font-medium text-ink-gray-9">{{ m.title }}</span>
            <Badge :label="m.status" :theme="statusTheme(m.status)" variant="subtle" />
            <Badge
              v-if="m.signoff_status"
              :label="signoffLabel(m.signoff_status)"
              :theme="signoffTheme(m.signoff_status)"
              variant="subtle"
            />
            <span
              v-if="editable && !m.customer_visible"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
            >
              <LucideEyeOff class="size-3" /> {{ __("Internal") }}
            </span>
            <span class="flex-1" />
            <span
              v-if="m.due_date"
              class="text-xs inline-flex items-center gap-1"
              :class="isOverdue(m) ? 'text-red-600 font-medium' : 'text-ink-gray-5'"
            >
              <LucideCalendar class="size-3.5" /> {{ m.due_date }}
            </span>
          </div>
          <div
            v-if="m.tasks_total"
            class="flex items-center gap-2 mt-1.5"
          >
            <div class="h-1.5 w-32 rounded-full bg-surface-gray-3 overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500"
                :style="{
                  width: (m.tasks_done / m.tasks_total) * 100 + '%',
                  backgroundColor: mColor(m.name).dot,
                }"
              />
            </div>
            <span class="text-[11px] text-ink-gray-5">
              {{ __("{0} of {1} tasks done", [m.tasks_done, m.tasks_total]) }}
            </span>
          </div>
          <p v-if="m.description && !isCollapsed(m.name)" class="text-xs text-ink-gray-6 mt-1 whitespace-pre-line">
            {{ m.description }}
          </p>
          <!-- Task list under the milestone (shown to agents and customers).
               The customer payload is { subject, status } only, so anything
               agent-only below is guarded on `editable`. -->
          <div
            v-if="visibleTasks(m).length && !isCollapsed(m.name)"
            class="mt-2 flex flex-col gap-1"
          >
            <div
              v-for="(t, ti) in visibleTasks(m)"
              :key="t.name || `${ti}-${t.subject}`"
              class="flex items-center gap-2 text-xs py-1 px-2 rounded-md border-l-2"
              :class="taskRowTone(t.status)"
            >
              <span
                class="size-3.5 rounded-full border-2 flex items-center justify-center shrink-0"
                :class="taskDotClass(t.status)"
              >
                <LucideCheck
                  v-if="t.status === 'Done'"
                  class="size-2 text-white"
                />
              </span>
              <span
                class="flex-1 min-w-0 truncate"
                :class="
                  t.status === 'Done'
                    ? 'line-through text-ink-gray-4'
                    : 'text-ink-gray-7'
                "
              >
                {{ t.subject }}
              </span>
              <span
                v-if="editable && t.responsibility"
                class="shrink-0 text-[10px] rounded px-1.5 py-0.5"
                :class="respClass(t.responsibility)"
                :title="__('Who does this work')"
              >
                {{ t.responsibility }}
              </span>
              <span
                v-if="t.status !== 'To Do'"
                class="shrink-0 text-[10px] rounded px-1.5 py-0.5"
                :class="taskStatusClass(t.status)"
              >
                {{ t.status }}
              </span>
              <button
                v-if="editable && t.name"
                type="button"
                class="shrink-0 rounded p-0.5 text-ink-gray-4 hover:text-ink-gray-8 hover:bg-surface-gray-2"
                :aria-label="__('Edit task: {0}', [t.subject])"
                :title="__('Edit task')"
                @click="editTask(m, t)"
              >
                <LucidePencil class="size-3" />
              </button>
            </div>
          </div>
          <p
            v-else-if="editable && respFilter && m.tasks?.length && !isCollapsed(m.name)"
            class="mt-2 text-[11px] text-ink-gray-4"
          >
            {{ __("No {0} tasks in this milestone", [__(respFilter)]) }}
          </p>
        </button>

        <!-- Client sign-off controls -->
        <div
          v-if="showSignoff(m)"
          class="px-3 pb-1 flex flex-wrap items-center gap-2"
        >
          <Button
            v-if="editable && m.signoff_status !== 'Approved'"
            size="sm"
            variant="subtle"
            theme="blue"
            :loading="signoffRes.loading"
            :disabled="m.signoff_status === 'Requested'"
            :label="
              m.signoff_status === 'Requested'
                ? __('Awaiting client sign-off')
                : __('Request client sign-off')
            "
            @click="requestSignoff(m)"
          />
          <template v-if="!editable && m.signoff_status === 'Requested'">
            <Button
              size="sm"
              variant="solid"
              theme="green"
              :loading="submitRes.loading"
              :label="__('Approve')"
              @click="approve(m)"
            />
            <Button
              size="sm"
              variant="subtle"
              :label="__('Request changes')"
              @click="openChanges(m)"
            />
          </template>
          <span
            v-if="m.signoff_status === 'Approved' && m.signed_off_on"
            class="text-[11px] text-green-700 inline-flex items-center gap-1"
          >
            <LucideCheck class="size-3" />
            {{ __("Signed off {0}", [fmtDate(m.signed_off_on)]) }}
          </span>
          <span
            v-else-if="m.signoff_status === 'Changes Requested'"
            class="text-[11px] text-amber-700"
          >
            {{ __("Changes requested") }}<template v-if="m.signoff_note">: {{ m.signoff_note }}</template>
          </span>
        </div>
        </div>
      </div>
    </div>
    <p v-else-if="!milestones.loading" class="text-sm text-ink-gray-5">
      {{ __("No milestones yet.") }}
    </p>

    <!-- Request changes dialog (customer) -->
    <Dialog
      v-model="showChanges"
      :options="{ title: __('Request changes') }"
    >
      <template #body-content>
        <FormControl
          v-model="changesNote"
          type="textarea"
          :label="__('What needs changing?')"
          :placeholder="__('Describe what should be revised…')"
        />
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :loading="submitRes.loading"
          :label="__('Send to the team')"
          @click="submitChanges"
        />
      </template>
    </Dialog>

    <!-- Create / edit dialog (agent) -->
    <Dialog
      v-if="editable"
      v-model="showDialog"
      :options="{ title: editing ? __('Edit milestone') : __('New milestone'), size: 'lg' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <FormControl v-model="form.title" :label="__('Title')" type="text" />
          <div class="grid grid-cols-3 gap-3">
            <FormControl
              v-model="form.status"
              :label="__('Status')"
              type="select"
              :options="statusOptions"
            />
            <FormControl v-model="form.due_date" :label="__('Due date')" type="date" />
            <FormControl
              v-model.number="form.sequence"
              :label="__('Order')"
              type="number"
            />
          </div>
          <FormControl
            v-model="form.description"
            :label="__('Description')"
            type="textarea"
          />
          <label class="flex items-center gap-2 text-sm text-ink-gray-7 cursor-pointer">
            <input v-model="form.customer_visible" type="checkbox" />
            {{ __("Visible to the customer") }}
          </label>

          <!-- Tasks in this milestone (existing milestones only) -->
          <div v-if="editing" class="border-t border-outline-gray-1 pt-3 flex flex-col gap-1.5">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-semibold text-ink-gray-7">
                {{ __("Tasks in this milestone") }}
                <span v-if="editingTasks.length" class="text-ink-gray-5 font-normal">
                  · {{ editingTasks.length }}
                </span>
              </span>
              <div v-if="editingTasks.length" class="flex items-center gap-1.5">
                <!-- Same filter as the timeline chips, reachable from inside
                     the dialog (which covers them). -->
                <select
                  v-model="respFilter"
                  class="text-[11px] rounded-md border border-outline-gray-2 bg-surface-white px-1.5 py-0.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                  :aria-label="__('Filter by responsibility')"
                >
                  <option value="">{{ __("All responsibilities") }}</option>
                  <option v-for="r in RESPONSIBILITIES" :key="r" :value="r">
                    {{ __(r) }}
                  </option>
                </select>
                <Button
                  variant="ghost"
                  size="sm"
                  :label="__('View on task board')"
                  @click="viewOnBoard"
                />
              </div>
            </div>
            <!-- Local rollup: moves the moment a row is edited. -->
            <div v-if="editingTasks.length" class="flex items-center gap-2">
              <div class="h-1 flex-1 rounded-full bg-surface-gray-3 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :style="{
                    width: (editingDone / editingTasks.length) * 100 + '%',
                    backgroundColor: mColor(editing).dot,
                  }"
                />
              </div>
              <span class="text-[11px] text-ink-gray-5 shrink-0">
                {{ __("{0} of {1} tasks done", [editingDone, editingTasks.length]) }}
              </span>
            </div>
            <p v-if="editingTasks.length" class="text-[11px] text-ink-gray-4">
              {{ __("Task changes save as you make them.") }}
              <template v-if="respFilter">
                ·
                {{
                  __("Showing {0} of {1} tasks", [
                    visibleEditingTasks.length,
                    editingTasks.length,
                  ])
                }}
              </template>
            </p>
            <div
              v-if="visibleEditingTasks.length"
              class="flex flex-col gap-1.5 max-h-72 overflow-y-auto pr-1"
            >
              <div
                v-for="(t, ti) in visibleEditingTasks"
                :key="t.name || `${ti}-${t.subject}`"
                class="rounded-lg border border-l-4 px-2.5 py-2 flex flex-col gap-1.5 transition-all duration-300"
                :class="[
                  t.name && savingTasks[t.name] ? 'opacity-60' : '',
                  t.name && t.name === focusTaskName
                    ? 'border-blue-400 ring-2 ring-blue-200 bg-surface-white'
                    : 'border-outline-gray-1 bg-surface-gray-1',
                  taskAccent(t.status),
                ]"
                :data-task="t.name"
              >
                <div class="flex items-center gap-2">
                  <span
                    class="size-3.5 rounded-full border-2 flex items-center justify-center shrink-0"
                    :class="taskDotClass(t.status)"
                  >
                    <LucideCheck v-if="t.status === 'Done'" class="size-2 text-white" />
                  </span>
                  <input
                    v-if="canEditTask(t)"
                    type="text"
                    :value="t.subject"
                    maxlength="500"
                    :aria-label="__('Task subject')"
                    class="flex-1 min-w-0 text-sm bg-transparent rounded-md border border-transparent px-1.5 py-0.5 hover:border-outline-gray-2 focus:border-blue-400 focus:bg-surface-white focus:outline-none"
                    :class="
                      t.status === 'Done'
                        ? 'line-through text-ink-gray-5'
                        : 'text-ink-gray-8'
                    "
                    @change="(e) => renameTask(t, e.target)"
                    @keyup.enter="(e) => e.target.blur()"
                  />
                  <span
                    v-else
                    class="flex-1 min-w-0 truncate text-sm"
                    :class="
                      t.status === 'Done'
                        ? 'line-through text-ink-gray-4'
                        : 'text-ink-gray-8'
                    "
                  >
                    {{ t.subject }}
                  </span>
                  <span
                    v-if="t.is_internal"
                    class="shrink-0 text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
                    :title="__('Hidden from the customer portal')"
                  >
                    <LucideEyeOff class="size-3" /> {{ __("Internal") }}
                  </span>
                  <!-- Rows without an id (customer payload) stay read-only. -->
                  <span
                    v-if="!canEditTask(t) && t.responsibility"
                    class="shrink-0 text-[10px] rounded px-1.5 py-0.5"
                    :class="respClass(t.responsibility)"
                    :title="__('Who does this work')"
                  >
                    {{ t.responsibility }}
                  </span>
                  <span
                    v-if="!canEditTask(t)"
                    class="shrink-0 text-[10px] rounded px-1.5 py-0.5"
                    :class="taskStatusClass(t.status)"
                  >
                    {{ t.status }}
                  </span>
                </div>

                <div
                  v-if="canEditTask(t)"
                  class="flex flex-wrap items-center gap-1.5 ps-[22px]"
                >
                  <select
                    :value="t.status"
                    class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                    :aria-label="__('Status')"
                    @change="(e) => patchTask(t, { status: e.target.value })"
                  >
                    <option v-for="s in TASK_STATUSES" :key="s" :value="s">
                      {{ __(s) }}
                    </option>
                  </select>
                  <select
                    :value="t.assigned_to || ''"
                    class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[140px]"
                    :aria-label="__('Assignee')"
                    @change="(e) => patchTask(t, { assigned_to: e.target.value })"
                  >
                    <option value="">{{ __("Unassigned") }}</option>
                    <option v-for="a in agentChoices(t)" :key="a.value" :value="a.value">
                      {{ a.label }}
                    </option>
                  </select>
                  <select
                    :value="t.priority || ''"
                    class="text-xs rounded-md border bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                    :class="priorityClass(t.priority)"
                    :aria-label="__('Priority')"
                    @change="(e) => patchTask(t, { priority: e.target.value })"
                  >
                    <option v-if="!t.priority" value="" disabled>
                      {{ __("Priority") }}
                    </option>
                    <option v-for="p in TASK_PRIORITIES" :key="p" :value="p">
                      {{ __(p) }}
                    </option>
                  </select>
                  <!-- Who does the work — not the same thing as "Internal",
                       which is about what the customer can see. -->
                  <select
                    :value="t.responsibility || 'Us'"
                    class="text-xs rounded-md border bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                    :class="respSelectClass(t.responsibility || 'Us')"
                    :aria-label="__('Responsibility')"
                    :title="__('Who does this work')"
                    @change="(e) => patchTask(t, { responsibility: e.target.value })"
                  >
                    <option v-for="r in RESPONSIBILITIES" :key="r" :value="r">
                      {{ __(r) }}
                    </option>
                  </select>
                  <div class="flex items-center gap-1">
                    <LucideCalendar
                      class="size-3.5"
                      :class="taskOverdue(t) ? 'text-red-600' : 'text-ink-gray-5'"
                    />
                    <input
                      type="date"
                      :value="t.end_date || ''"
                      class="text-xs rounded-md border bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                      :class="
                        taskOverdue(t)
                          ? 'border-red-300 text-red-600'
                          : 'border-outline-gray-2 text-ink-gray-7'
                      "
                      :aria-label="__('Due date')"
                      @change="(e) => patchTask(t, { end_date: e.target.value })"
                    />
                  </div>
                </div>
              </div>
            </div>
            <p v-else-if="editingTasks.length" class="text-xs text-ink-gray-4">
              {{ __("No {0} tasks in this milestone", [__(respFilter)]) }}
            </p>
            <p v-else class="text-xs text-ink-gray-4">
              {{ __("No tasks yet — add tasks to this milestone from the task board below.") }}
            </p>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex items-center gap-2 w-full">
          <Button
            v-if="editing"
            theme="red"
            variant="ghost"
            :label="__('Delete')"
            @click="remove"
          />
          <Button
            variant="solid"
            theme="blue"
            class="flex-1"
            :loading="saveRes.loading || createRes.loading"
            :label="editing ? __('Save') : __('Create milestone')"
            @click="submit"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, nextTick } from "vue";
import LucidePencil from "~icons/lucide/pencil";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createListResource,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { __ } from "@/translation";
import { buildMilestoneColors, milestoneColorOf } from "@/utils";
import LucidePlus from "~icons/lucide/plus";
import LucideCheck from "~icons/lucide/check";
import LucideFlag from "~icons/lucide/flag";
import LucideCalendar from "~icons/lucide/calendar";
import LucideEyeOff from "~icons/lucide/eye-off";
import LucideChevronRight from "~icons/lucide/chevron-right";
import { useMilestoneCollapse } from "@/composables/useMilestoneCollapse";

interface P {
  projectId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });

// Folding a milestone hides its description and task list — here and in the
// timeline, which reads the same state.
const { isCollapsed, toggle, setAll } = useMilestoneCollapse(
  () => props.projectId
);
const milestoneNames = computed(() =>
  (milestones.data || []).map((m: any) => m.name)
);
const allCollapsed = computed(
  () =>
    !!milestoneNames.value.length &&
    milestoneNames.value.every((n: string) => isCollapsed(n))
);
function toggleAll() {
  setAll(milestoneNames.value, !allCollapsed.value);
}
const emit = defineEmits(["changed", "view-tasks"]);

const STATUSES = ["Upcoming", "In Progress", "Completed", "Missed"];
const statusOptions = STATUSES.map((s) => ({ label: s, value: s }));

const milestones = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: props.projectId }),
  auto: true,
});
watch(
  () => props.projectId,
  () => milestones.reload()
);

defineExpose({ reload: () => milestones.reload(), data: milestones });

// Each milestone gets a distinct colour, keyed by its order in the project.
const milestoneColors = computed(() =>
  buildMilestoneColors((milestones.data || []).map((m: any) => m.name))
);
function mColor(name: string | null | undefined) {
  return milestoneColorOf(name, milestoneColors.value);
}

function dotClass(status: string) {
  return (
    {
      Upcoming: "border-outline-gray-3 bg-surface-white",
      "In Progress": "border-blue-500 bg-blue-100",
      Completed: "border-green-500 bg-green-500",
      Missed: "border-red-500 bg-red-100",
    }[status] || "border-outline-gray-3 bg-surface-white"
  );
}
function statusTheme(status: string) {
  return (
    {
      Upcoming: "gray",
      "In Progress": "blue",
      Completed: "green",
      Missed: "red",
    }[status] || "gray"
  );
}
function isOverdue(m: any) {
  if (!m.due_date || m.status === "Completed") return false;
  return dayjs(m.due_date).isBefore(dayjs().startOf("day"));
}

function taskStatusClass(status: string) {
  return (
    {
      "In Progress": "bg-blue-50 text-blue-700",
      Done: "bg-green-50 text-green-700",
      Pending: "bg-amber-50 text-amber-700",
      Postponed: "bg-violet-50 text-violet-700",
    }[status] || "bg-surface-gray-2 text-ink-gray-6"
  );
}
// Whole-row status colour on the timeline — same palette as the status chips.
function taskRowTone(status: string) {
  return (
    {
      "In Progress": "bg-blue-50 border-l-blue-400",
      Done: "bg-green-50 border-l-green-500",
      Pending: "bg-amber-50 border-l-amber-400",
      Postponed: "bg-violet-50 border-l-violet-400",
    }[status] || "border-l-outline-gray-3"
  );
}
// Left-edge accent for the dialog rows, which keep their neutral fill.
function taskAccent(status: string) {
  return (
    {
      "In Progress": "border-l-blue-400",
      Done: "border-l-green-500",
      Pending: "border-l-amber-400",
      Postponed: "border-l-violet-400",
    }[status] || "border-l-outline-gray-3"
  );
}
function taskDotClass(status: string) {
  return (
    {
      "In Progress": "border-blue-400 bg-blue-50",
      Done: "border-green-500 bg-green-500",
      Pending: "border-amber-400 bg-amber-50",
      Postponed: "border-violet-400 bg-violet-50",
    }[status] || "border-outline-gray-3 bg-surface-white"
  );
}
function priorityClass(priority: string) {
  return (
    {
      Urgent: "border-red-300 text-red-700",
      High: "border-orange-300 text-orange-700",
    }[priority] || "border-outline-gray-2 text-ink-gray-7"
  );
}
function taskOverdue(t: any) {
  if (!t?.end_date || t.status === "Done") return false;
  return dayjs(t.end_date).isBefore(dayjs().startOf("day"));
}

// --- Responsibility: who does the work, us (the implementor) or the client ---
// Deliberately separate from `is_internal`, which is about what the customer
// can see. Agent-only: the field is scrubbed from customer payloads, so every
// use of it below is guarded on `editable` (or on the value being present).
const RESPONSIBILITIES = ["Us", "Client", "Joint"];
const respFilter = ref("");
const respFilterOptions = computed(() => [
  { value: "", label: __("All") },
  ...RESPONSIBILITIES.map((r) => ({ value: r, label: __(r) })),
]);
function respClass(r: string) {
  return (
    {
      Us: "bg-blue-50 text-blue-700",
      Client: "bg-amber-50 text-amber-700",
      Joint: "bg-violet-50 text-violet-700",
    }[r] || "bg-surface-gray-2 text-ink-gray-6"
  );
}
function respSelectClass(r: string) {
  return (
    {
      Us: "border-blue-200 text-blue-700",
      Client: "border-amber-300 text-amber-700",
      Joint: "border-violet-300 text-violet-700",
    }[r] || "border-outline-gray-2 text-ink-gray-7"
  );
}
function respChipActiveClass(r: string) {
  return (
    {
      Us: "border-blue-200 bg-blue-50 text-blue-700",
      Client: "border-amber-200 bg-amber-50 text-amber-700",
      Joint: "border-violet-200 bg-violet-50 text-violet-700",
    }[r] || "border-outline-gray-3 bg-surface-gray-2 text-ink-gray-8"
  );
}
// Rows written before the field existed come back blank; the stored default is
// "Us", so they filter as "Us" (the badge still only shows a real value).
function matchesResp(t: any) {
  if (!respFilter.value) return true;
  return (t?.responsibility || "Us") === respFilter.value;
}
/** Task rows of a milestone that pass the responsibility filter. Customers
 * never see the filter (and have no such field), so nothing is hidden there. */
function visibleTasks(m: any) {
  const tasks = m?.tasks || [];
  return respFilter.value ? tasks.filter(matchesResp) : tasks;
}
// Only the milestone tracker needs this; customers have no filter row.
const anyTasks = computed(() =>
  (milestones.data || []).some((m: any) => m.tasks?.length)
);

// --- create / edit ---
const showDialog = ref(false);
const editing = ref<string | null>(null);
// Tasks of the milestone being edited, as returned by get_milestones.
const editingTasks = ref<any[]>([]);
const form = reactive({
  title: "",
  status: "Upcoming",
  due_date: "",
  sequence: 0,
  description: "",
  customer_visible: true,
});

function openCreate() {
  editing.value = null;
  editingTasks.value = [];
  Object.assign(form, {
    title: "",
    status: "Upcoming",
    due_date: "",
    sequence: (milestones.data?.length || 0) + 1,
    description: "",
    customer_visible: true,
  });
  showDialog.value = true;
}
// Pencil on a timeline row: open this milestone's editor with that task
// scrolled into view, highlighted, and its subject ready to type into.
const focusTaskName = ref<string | null>(null);
let focusTimer: ReturnType<typeof setTimeout> | undefined;
function editTask(m: any, t: any) {
  openEdit(m);
  focusTaskName.value = t.name;
  clearTimeout(focusTimer);
  focusTimer = setTimeout(() => (focusTaskName.value = null), 2500);
  // The dialog renders through a teleport and animates in, so give the row
  // a beat to exist before reaching for it.
  nextTick(() =>
    setTimeout(() => {
      const row = document.querySelector<HTMLElement>(
        `[data-task="${CSS.escape(t.name)}"]`
      );
      row?.scrollIntoView({ block: "center", behavior: "smooth" });
      row?.querySelector<HTMLInputElement>('input[type="text"]')?.focus();
    }, 150)
  );
}
function openEdit(m: any) {
  editing.value = m.name;
  // Detached copies: inline edits below are saved straight away, so the rows
  // must not be clobbered when the milestones resource reloads underneath us.
  editingTasks.value = (m.tasks || []).map((t: any) => ({ ...t }));
  Object.assign(form, {
    title: m.title || "",
    status: m.status || "Upcoming",
    due_date: m.due_date || "",
    sequence: m.sequence || 0,
    description: m.description || "",
    customer_visible: !!m.customer_visible,
  });
  showDialog.value = true;
}

function reload() {
  milestones.reload();
  emit("changed");
}

// --- inline task editing inside the edit dialog (agents only) ---
const TASK_STATUSES = ["To Do", "In Progress", "Pending", "Postponed", "Done"];
const TASK_PRIORITIES = ["Low", "Medium", "High", "Urgent"];

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
// Keep a task's current assignee selectable even if that agent is inactive.
function agentChoices(t: any) {
  const options = agentOptions.value;
  if (t?.assigned_to && !options.some((a: any) => a.value === t.assigned_to)) {
    return [
      { value: t.assigned_to, label: t.assigned_to_name || t.assigned_to },
      ...options,
    ];
  }
  return options;
}
function agentLabel(id: string) {
  return agentOptions.value.find((a: any) => a.value === id)?.label || "";
}

// Customers get { subject, status } only — no id, so those rows are read-only.
function canEditTask(t: any) {
  return !!(props.editable && t && t.name);
}

const editingDone = computed(
  () => editingTasks.value.filter((t: any) => t.status === "Done").length
);
// The responsibility filter hides rows only; the rollup above still counts the
// whole milestone, so it never disagrees with the timeline's progress bar.
const visibleEditingTasks = computed(() =>
  respFilter.value ? editingTasks.value.filter(matchesResp) : editingTasks.value
);

const savingTasks = reactive<Record<string, boolean>>({});
// One save at a time per task, so two quick edits to the same row can't race
// each other into a "document has been modified" error.
const taskSaveChain: Record<string, Promise<any>> = {};
const taskUpdateRes = createResource({
  url: "helpdesk.api.addon.update_task",
  // Failures are handled per row in patchTask() — it reverts the row and
  // toasts. Without an onError here frappe-ui treats the error as unhandled
  // and runs the app-wide fallback handler too, so the user gets two toasts.
  onError: () => {},
});

/** Save one task field straight away; revert the row if the server says no. */
function patchTask(t: any, fields: Record<string, any>) {
  if (!canEditTask(t)) return;
  const previous: Record<string, any> = {};
  const changed: Record<string, any> = {};
  for (const [key, value] of Object.entries(fields)) {
    if ((t[key] ?? "") === (value ?? "")) continue;
    previous[key] = t[key];
    changed[key] = value;
  }
  if (!Object.keys(changed).length) return;
  const name = t.name;
  const prevAssigneeName = t.assigned_to_name;
  // Optimistic: the row shows the edit while the save is in flight.
  Object.assign(t, changed);
  if ("assigned_to" in changed) {
    t.assigned_to_name = agentLabel(changed.assigned_to);
  }
  savingTasks[name] = true;
  const run: Promise<any> = (taskSaveChain[name] || Promise.resolve())
    .catch(() => {})
    .then(() => taskUpdateRes.submit({ name, ...changed }))
    .then(() => {
      // Roll the milestone's "X of Y tasks done" bar forward.
      reload();
    })
    .catch((e: any) => {
      Object.assign(t, previous);
      if ("assigned_to" in changed) t.assigned_to_name = prevAssigneeName;
      toast.error(e?.messages?.[0] || __("Could not update task"));
    })
    .finally(() => {
      if (taskSaveChain[name] === run) {
        delete taskSaveChain[name];
        delete savingTasks[name];
      }
    });
  taskSaveChain[name] = run;
}
function renameTask(t: any, el: HTMLInputElement) {
  const subject = (el.value || "").trim();
  if (!subject || subject === t.subject) {
    // Blank or unchanged: put the stored subject back in the box.
    el.value = t.subject || "";
    return;
  }
  patchTask(t, { subject });
}

const createRes = createResource({
  url: "helpdesk.api.project.add_milestone",
  onSuccess: () => {
    showDialog.value = false;
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save milestone")),
});
const saveRes = createResource({
  url: "helpdesk.api.project.update_milestone",
  onSuccess: () => {
    showDialog.value = false;
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save milestone")),
});
const deleteRes = createResource({
  url: "helpdesk.api.project.delete_milestone",
  onSuccess: () => {
    showDialog.value = false;
    reload();
  },
});

// --- Client sign-off ---
const signoffRes = createResource({
  url: "helpdesk.api.project.request_milestone_signoff",
  onSuccess: () => reload(),
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not request sign-off")),
});
const submitRes = createResource({
  url: "helpdesk.api.project.submit_milestone_signoff",
  onSuccess: () => {
    showChanges.value = false;
    reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not submit sign-off")),
});
const showChanges = ref(false);
const changesMilestone = ref<string | null>(null);
const changesNote = ref("");

function showSignoff(m: any) {
  // Agents: on client-facing milestones. Customers: once sign-off is in play.
  return props.editable ? !!m.customer_visible : !!m.signoff_status;
}
function requestSignoff(m: any) {
  signoffRes.submit({ name: m.name });
}
function approve(m: any) {
  submitRes.submit({ name: m.name, approved: 1 });
}
function openChanges(m: any) {
  changesMilestone.value = m.name;
  changesNote.value = "";
  showChanges.value = true;
}
function submitChanges() {
  if (!changesMilestone.value) return;
  submitRes.submit({
    name: changesMilestone.value,
    approved: 0,
    note: changesNote.value,
  });
}
function signoffLabel(s: string) {
  return (
    {
      Requested: __("Sign-off requested"),
      Approved: __("Client approved"),
      "Changes Requested": __("Changes requested"),
    }[s] || s
  );
}
function signoffTheme(s: string) {
  return { Requested: "orange", Approved: "green", "Changes Requested": "red" }[s] || "gray";
}
function fmtDate(d: string) {
  return dayjs(d).format("MMM D, YYYY");
}

// Saves the milestone only. Task rows save themselves as they are edited, so
// nothing here re-sends (or overwrites) them.
function submit() {
  if (!form.title.trim()) {
    toast.error(__("Milestone title is required"));
    return;
  }
  const payload = {
    title: form.title.trim(),
    status: form.status,
    due_date: form.due_date || "",
    sequence: form.sequence || 0,
    description: form.description || "",
    customer_visible: form.customer_visible ? 1 : 0,
  };
  if (editing.value) {
    saveRes.submit({ name: editing.value, ...payload });
  } else {
    createRes.submit({ project: props.projectId, ...payload });
  }
}
function remove() {
  if (editing.value) deleteRes.submit({ name: editing.value });
}

// Jump to the task board filtered to the milestone being viewed.
function viewOnBoard() {
  if (!editing.value) return;
  const milestone = editing.value;
  showDialog.value = false;
  emit("view-tasks", milestone);
}
</script>
