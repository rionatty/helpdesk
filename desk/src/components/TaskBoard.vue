<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-green-100 text-green-700 flex items-center justify-center"
        >
          <LucideListChecks class="size-4" />
        </div>
        <span class="text-sm font-semibold text-ink-gray-8">
          {{ __("Tasks") }}
        </span>
        <span v-if="tasks.data?.length" class="text-xs text-ink-gray-5">
          · {{ tasks.data.length }}
        </span>
      </div>
      <select
        v-if="milestoneOptions.length"
        v-model="milestoneFilter"
        class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
      >
        <option value="">{{ __("All milestones") }}</option>
        <option v-for="m in milestoneOptions" :key="m.value" :value="m.value">
          {{ m.label }}
        </option>
      </select>
    </div>

    <!-- Kanban columns -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <div
        v-for="col in COLUMNS"
        :key="col.key"
        class="rounded-xl bg-surface-gray-1 border border-outline-gray-1 p-2.5 flex flex-col gap-2 min-h-[80px]"
      >
        <div class="flex items-center justify-between px-1">
          <div class="flex items-center gap-1.5 text-xs font-semibold text-ink-gray-7">
            <span class="size-2 rounded-full" :class="col.dot" />
            {{ col.key }}
            <span class="text-ink-gray-4">{{ grouped[col.key].length }}</span>
          </div>
          <button
            v-if="editable"
            type="button"
            class="text-ink-gray-5 hover:text-ink-gray-8"
            :aria-label="__('Add task')"
            @click="quickAdd(col.key)"
          >
            <LucidePlus class="size-3.5" />
          </button>
        </div>

        <button
          v-for="t in grouped[col.key]"
          :key="t.name"
          type="button"
          class="text-start rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2.5 flex flex-col gap-2 hover:shadow-sm hover:border-outline-gray-3 transition-all"
          @click="open(t)"
        >
          <div class="text-sm font-medium text-ink-gray-8 leading-snug">
            {{ t.subject }}
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              class="text-[10px] font-medium rounded-full px-1.5 py-0.5"
              :class="priorityClass(t.priority)"
            >
              {{ t.priority }}
            </span>
            <span
              v-if="t.end_date"
              class="text-[10px] rounded-full px-1.5 py-0.5 inline-flex items-center gap-0.5"
              :class="
                isOverdue(t)
                  ? 'bg-red-100 text-red-700'
                  : 'bg-surface-gray-2 text-ink-gray-6'
              "
            >
              <LucideCalendar class="size-3" /> {{ t.end_date }}
            </span>
            <span
              v-if="t.comment_count"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
            >
              <LucideMessageCircle class="size-3" /> {{ t.comment_count }}
            </span>
            <span
              v-if="t.milestone && milestoneTitle(t.milestone)"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-violet-100 text-violet-700 inline-flex items-center gap-0.5"
            >
              <LucideFlag class="size-3" /> {{ milestoneTitle(t.milestone) }}
            </span>
            <span
              v-if="t.is_internal && editable"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
              :title="__('Hidden from the customer portal')"
            >
              <LucideEyeOff class="size-3" /> {{ __("Internal") }}
            </span>
          </div>
          <div
            v-if="t.assigned_to_name"
            class="flex items-center gap-1.5 text-[11px] text-ink-gray-5"
          >
            <Avatar size="xs" :label="t.assigned_to_name" />
            {{ t.assigned_to_name }}
          </div>
        </button>

        <div
          v-if="!grouped[col.key].length"
          class="text-[11px] text-ink-gray-4 px-1 py-1"
        >
          {{ __("Nothing here") }}
        </div>
      </div>
    </div>

    <!-- Add task (agent) -->
    <form
      v-if="editable"
      class="flex items-center gap-2 mt-1"
      @submit.prevent="add"
    >
      <input
        v-model="newSubject"
        type="text"
        :placeholder="__('Add a task…')"
        class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
      />
      <Button
        :label="__('Add')"
        theme="blue"
        variant="subtle"
        size="sm"
        :loading="addRes.loading"
        @click="add"
      />
    </form>

    <!-- Task detail dialog -->
    <Dialog v-model="showDetail" :options="{ size: '2xl' }">
      <template #body>
        <div v-if="selected" class="p-5 flex flex-col gap-4">
          <!-- Title -->
          <div class="flex items-start justify-between gap-3">
            <input
              v-if="editable"
              :value="selected.subject"
              class="flex-1 text-lg font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
              @change="(e) => patch({ subject: e.target.value })"
            />
            <h2 v-else class="flex-1 text-lg font-semibold text-ink-gray-9">
              {{ selected.subject }}
            </h2>
            <button
              v-if="editable"
              type="button"
              class="text-ink-gray-4 hover:text-ink-red-3 shrink-0 mt-1"
              :aria-label="__('Delete task')"
              @click="remove"
            >
              <LucideTrash2 class="size-4" />
            </button>
          </div>

          <!-- Fields -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Status") }}</span>
              <select
                v-if="editable"
                :value="selected.status"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ status: e.target.value })"
              >
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">{{ selected.status }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Priority") }}</span>
              <select
                v-if="editable"
                :value="selected.priority"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ priority: e.target.value })"
              >
                <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">{{ selected.priority }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Start") }}</span>
              <input
                v-if="editable"
                type="date"
                :value="selected.start_date || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ start_date: e.target.value })"
              />
              <span v-else class="text-sm text-ink-gray-8">
                {{ selected.start_date || "—" }}
              </span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Due") }}</span>
              <input
                v-if="editable"
                type="date"
                :value="selected.end_date || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ end_date: e.target.value })"
              />
              <span v-else class="text-sm text-ink-gray-8">
                {{ selected.end_date || "—" }}
              </span>
            </div>
          </div>

          <!-- Placement: milestone / feature -->
          <div
            v-if="milestoneOptions.length || featureOptions.length"
            class="grid grid-cols-2 gap-3"
          >
            <div v-if="milestoneOptions.length" class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Milestone") }}</span>
              <select
                v-if="editable"
                :value="selected.milestone || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ milestone: e.target.value })"
              >
                <option value="">{{ __("No milestone") }}</option>
                <option v-for="m in milestoneOptions" :key="m.value" :value="m.value">
                  {{ m.label }}
                </option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">
                {{ milestoneTitle(selected.milestone) || "—" }}
              </span>
            </div>
            <div v-if="featureOptions.length" class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Feature") }}</span>
              <select
                v-if="editable"
                :value="selected.feature || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ feature: e.target.value })"
              >
                <option value="">{{ __("No feature") }}</option>
                <option v-for="f in featureOptions" :key="f.value" :value="f.value">
                  {{ f.label }}
                </option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">
                {{ featureTitle(selected.feature) || "—" }}
              </span>
            </div>
          </div>

          <!-- Internal toggle (agent) -->
          <label
            v-if="editable"
            class="flex items-center gap-2 text-sm text-ink-gray-7 cursor-pointer"
          >
            <input
              type="checkbox"
              :checked="!!selected.is_internal"
              @change="(e) => patch({ is_internal: e.target.checked ? 1 : 0 })"
            />
            {{ __("Internal only — hidden from the customer portal") }}
          </label>

          <!-- Assignee (agent) -->
          <div v-if="editable" class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Assignee") }}</span>
            <select
              :value="selected.assigned_to || ''"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              @change="(e) => patch({ assigned_to: e.target.value })"
            >
              <option value="">{{ __("Unassigned") }}</option>
              <option v-for="a in agentOptions" :key="a.value" :value="a.value">
                {{ a.label }}
              </option>
            </select>
          </div>
          <div
            v-else-if="selected.assigned_to_name"
            class="flex items-center gap-2 text-sm text-ink-gray-7"
          >
            <Avatar size="sm" :label="selected.assigned_to_name" />
            {{ selected.assigned_to_name }}
          </div>

          <!-- Description -->
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Description") }}</span>
            <textarea
              v-if="editable"
              :value="selected.description || ''"
              rows="2"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
              @change="(e) => patch({ description: e.target.value })"
            />
            <p v-else class="text-sm text-ink-gray-8 whitespace-pre-line">
              {{ selected.description || __("No description.") }}
            </p>
          </div>

          <!-- Comments -->
          <div class="border-t border-outline-gray-1 pt-3 flex flex-col gap-3">
            <div class="text-sm font-semibold text-ink-gray-8">
              {{ __("Comments") }}
            </div>
            <div
              v-if="comments.data?.length"
              class="flex flex-col gap-3 max-h-60 overflow-y-auto"
            >
              <div v-for="c in comments.data" :key="c.name" class="flex gap-2.5">
                <Avatar size="sm" :label="c.author" class="mt-0.5 shrink-0" />
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-ink-gray-8">
                      {{ c.author }}
                    </span>
                    <span class="text-xs text-ink-gray-4">
                      {{ timeAgo(c.creation) }}
                    </span>
                  </div>
                  <p class="text-sm text-ink-gray-7 whitespace-pre-line">
                    {{ c.content }}
                  </p>
                </div>
              </div>
            </div>
            <p v-else-if="!comments.loading" class="text-sm text-ink-gray-5">
              {{ __("No comments yet.") }}
            </p>
            <form class="flex items-center gap-2" @submit.prevent="addComment">
              <input
                v-model="newComment"
                type="text"
                :placeholder="__('Write a comment…')"
                class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
              />
              <Button
                :label="__('Send')"
                theme="blue"
                variant="solid"
                size="sm"
                :loading="addCommentRes.loading"
                @click="addComment"
              />
            </form>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Avatar,
  Button,
  Dialog,
  createListResource,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { timeAgo } from "@/utils";
import { __ } from "@/translation";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideCalendar from "~icons/lucide/calendar";
import LucideMessageCircle from "~icons/lucide/message-circle";
import LucideFlag from "~icons/lucide/flag";
import LucideEyeOff from "~icons/lucide/eye-off";
import LucideListChecks from "~icons/lucide/list-checks";

interface P {
  addonId?: string;
  projectId?: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), {
  addonId: "",
  projectId: "",
  editable: false,
});
const emit = defineEmits(["changed"]);

const STATUSES = ["To Do", "In Progress", "Done", "Blocked"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];
const COLUMNS = [
  { key: "To Do", dot: "bg-ink-gray-4" },
  { key: "In Progress", dot: "bg-blue-500" },
  { key: "Done", dot: "bg-green-500" },
  { key: "Blocked", dot: "bg-red-500" },
];

const parentParams = () =>
  props.addonId ? { addon: props.addonId } : { project: props.projectId };

const tasks = createResource({
  url: "helpdesk.api.addon.get_tasks",
  makeParams: () => parentParams(),
  auto: true,
});
watch(
  () => [props.addonId, props.projectId],
  () => {
    tasks.reload();
    if (props.projectId) milestonesRes.reload();
    if (props.addonId) featuresRes.reload();
  }
);

const milestoneFilter = ref("");

const grouped = computed(() => {
  const g: Record<string, any[]> = {
    "To Do": [],
    "In Progress": [],
    Done: [],
    Blocked: [],
  };
  (tasks.data || [])
    .filter((t: any) => !milestoneFilter.value || t.milestone === milestoneFilter.value)
    .forEach((t: any) => (g[t.status] || g["To Do"]).push(t));
  return g;
});

// --- milestone / feature context for placement + chips ---
const milestonesRes = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: props.projectId }),
  auto: !!props.projectId,
});
const featuresRes = createResource({
  url: "helpdesk.api.addon.get_features",
  makeParams: () => ({ addon: props.addonId }),
  auto: !!props.addonId,
});
const milestoneOptions = computed(() =>
  (milestonesRes.data || []).map((m: any) => ({ value: m.name, label: m.title }))
);
const featureOptions = computed(() =>
  (featuresRes.data || []).map((f: any) => ({
    value: f.name,
    label: f.feature_title,
  }))
);
function milestoneTitle(name: string) {
  return (milestonesRes.data || []).find((m: any) => m.name === name)?.title;
}
defineExpose({
  refreshMilestones: () => props.projectId && milestonesRes.reload(),
});
function featureTitle(name: string) {
  return (featuresRes.data || []).find((f: any) => f.name === name)?.feature_title;
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

function priorityClass(p: string) {
  return (
    {
      Urgent: "bg-red-100 text-red-700",
      High: "bg-orange-100 text-orange-700",
      Medium: "bg-blue-100 text-blue-700",
      Low: "bg-surface-gray-2 text-ink-gray-6",
    }[p] || "bg-surface-gray-2 text-ink-gray-6"
  );
}
function isOverdue(t: any) {
  if (!t.end_date || t.status === "Done") return false;
  return dayjs(t.end_date).isBefore(dayjs().startOf("day"));
}

function reload() {
  tasks.reload();
  if (props.projectId) milestonesRes.reload();
  emit("changed");
}

const newSubject = ref("");
const addRes = createResource({
  url: "helpdesk.api.addon.add_task",
  onSuccess: () => {
    newSubject.value = "";
    reload();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not add task")),
});
function add() {
  const s = newSubject.value.trim();
  if (!s) return;
  addRes.submit({ ...parentParams(), subject: s });
}
function quickAdd(status: string) {
  const s = (newSubject.value || __("New task")).trim();
  addRes.submit({ ...parentParams(), subject: s, status });
  newSubject.value = "";
}

// --- detail dialog ---
const showDetail = ref(false);
const selected = ref<any>(null);

const comments = createResource({
  url: "helpdesk.api.addon.get_task_comments",
  makeParams: () => ({ task: selected.value?.name }),
});
function open(t: any) {
  selected.value = { ...t };
  showDetail.value = true;
  comments.reload();
}

const updateRes = createResource({
  url: "helpdesk.api.addon.update_task",
  onSuccess: () => {
    tasks.reload();
    if (props.projectId) milestonesRes.reload();
    emit("changed");
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update task")),
});
function patch(fields: Record<string, any>) {
  if (!selected.value) return;
  Object.assign(selected.value, fields);
  updateRes.submit({ name: selected.value.name, ...fields });
}

const deleteRes = createResource({
  url: "helpdesk.api.addon.delete_task",
  onSuccess: () => {
    showDetail.value = false;
    reload();
  },
});
function remove() {
  if (selected.value) deleteRes.submit({ name: selected.value.name });
}

const newComment = ref("");
const addCommentRes = createResource({
  url: "helpdesk.api.addon.add_task_comment",
  onSuccess: () => {
    newComment.value = "";
    comments.reload();
    tasks.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not post comment")),
});
function addComment() {
  const c = newComment.value.trim();
  if (!c || !selected.value) return;
  addCommentRes.submit({ task: selected.value.name, content: c });
}
</script>
