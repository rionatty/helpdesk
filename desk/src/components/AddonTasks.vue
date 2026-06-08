<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <div class="text-sm font-semibold text-ink-gray-8">{{ __("Tasks") }}</div>
      <span v-if="tasks.data?.length" class="text-xs text-ink-gray-5">
        {{ doneCount }}/{{ tasks.data.length }} {{ __("done") }}
      </span>
    </div>

    <div v-if="tasks.data?.length" class="flex flex-col gap-2">
      <div
        v-for="t in tasks.data"
        :key="t.name"
        class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5 flex flex-col gap-2"
      >
        <div class="flex items-start gap-2">
          <span
            class="text-sm flex-1 font-medium leading-snug"
            :class="t.status === 'Done' ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
          >
            {{ t.subject }}
          </span>
          <Badge :label="t.priority" :theme="priorityTheme(t.priority)" variant="subtle" />
          <button
            type="button"
            class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
            :aria-label="__('Delete task')"
            @click="remove(t.name)"
          >
            <LucideTrash2 class="size-3.5" />
          </button>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
          <select
            :value="t.status"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            @change="(e) => patch(t.name, { status: e.target.value })"
          >
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
          <select
            :value="t.priority"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            @change="(e) => patch(t.name, { priority: e.target.value })"
          >
            <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
          </select>
          <select
            :value="t.assigned_to || ''"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            :aria-label="__('Assignee')"
            @change="(e) => patch(t.name, { assigned_to: e.target.value })"
          >
            <option value="">{{ __("Unassigned") }}</option>
            <option v-for="a in agentOptions" :key="a.value" :value="a.value">
              {{ a.label }}
            </option>
          </select>
          <div class="flex items-center gap-1">
            <input
              type="date"
              :value="t.start_date || ''"
              :aria-label="__('Start date')"
              class="w-full text-xs rounded-md border border-outline-gray-2 bg-surface-white px-1.5 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              @change="(e) => patch(t.name, { start_date: e.target.value })"
            />
            <input
              type="date"
              :value="t.end_date || ''"
              :aria-label="__('Due date')"
              class="w-full text-xs rounded-md border bg-surface-white px-1.5 py-1 focus:outline-none focus:border-blue-400"
              :class="isOverdue(t) ? 'border-red-300 text-ink-red-3' : 'border-outline-gray-2 text-ink-gray-7'"
              @change="(e) => patch(t.name, { end_date: e.target.value })"
            />
          </div>
        </div>
        <div
          v-if="t.assigned_to_name"
          class="text-xs text-ink-gray-5 inline-flex items-center gap-1.5"
        >
          <Avatar size="xs" :label="t.assigned_to_name" />
          {{ t.assigned_to_name }}
        </div>
      </div>
    </div>
    <div v-else-if="!tasks.loading" class="text-xs text-ink-gray-5">
      {{ __("No tasks yet — break the work into trackable tasks below.") }}
    </div>

    <form class="flex items-center gap-2 mt-1" @submit.prevent="add">
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

interface P {
  addonId: string;
}
const props = defineProps<P>();
const emit = defineEmits(["changed"]);

const STATUSES = ["To Do", "In Progress", "Done", "Blocked"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];
const newSubject = ref("");

const tasks = createResource({
  url: "helpdesk.api.addon.get_tasks",
  makeParams: () => ({ addon: props.addonId }),
  auto: true,
});
watch(() => props.addonId, () => tasks.reload());

const doneCount = computed(
  () => (tasks.data || []).filter((t: any) => t.status === "Done").length
);

const agents = createListResource({
  doctype: "HD Agent",
  fields: ["name", "agent_name"],
  filters: { is_active: 1 },
  pageLength: 500,
  auto: true,
});
const agentOptions = computed(() =>
  (agents.data || []).map((a: any) => ({
    value: a.name,
    label: a.agent_name || a.name,
  }))
);

function reload() {
  tasks.reload();
  emit("changed");
}

function priorityTheme(p: string) {
  return { Urgent: "red", High: "orange", Medium: "blue", Low: "gray" }[p] || "gray";
}
function isOverdue(t: any) {
  if (!t.end_date || t.status === "Done") return false;
  return dayjs(t.end_date).isBefore(dayjs().startOf("day"));
}

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
  addRes.submit({ addon: props.addonId, subject: s });
}

const updateRes = createResource({
  url: "helpdesk.api.addon.update_task",
  onSuccess: () => reload(),
});
function patch(name: string, fields: Record<string, any>) {
  updateRes.submit({ name, ...fields });
}

const deleteRes = createResource({
  url: "helpdesk.api.addon.delete_task",
  onSuccess: () => reload(),
});
function remove(name: string) {
  deleteRes.submit({ name });
}
</script>
