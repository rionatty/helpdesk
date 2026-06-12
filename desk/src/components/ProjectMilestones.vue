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
        <!-- Rail -->
        <div class="flex flex-col items-center w-5 shrink-0">
          <span
            class="size-4 rounded-full border-2 shrink-0 mt-1.5 flex items-center justify-center"
            :class="dotClass(m.status)"
          >
            <LucideCheck
              v-if="m.status === 'Completed'"
              class="size-2.5 text-white"
            />
          </span>
          <span
            v-if="i < milestones.data.length - 1"
            class="w-0.5 flex-1 my-0.5"
            :class="m.status === 'Completed' ? 'bg-green-400' : 'bg-outline-gray-2'"
          />
        </div>

        <!-- Body -->
        <button
          type="button"
          class="flex-1 text-start rounded-lg px-3 py-2 mb-2 -mt-0.5 transition-colors"
          :class="editable ? 'hover:bg-surface-menu-bar' : 'cursor-default'"
          @click="editable && openEdit(m)"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium text-ink-gray-9">{{ m.title }}</span>
            <Badge :label="m.status" :theme="statusTheme(m.status)" variant="subtle" />
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
                class="h-full rounded-full bg-green-500 transition-all duration-500"
                :style="{ width: (m.tasks_done / m.tasks_total) * 100 + '%' }"
              />
            </div>
            <span class="text-[11px] text-ink-gray-5">
              {{ __("{0} of {1} tasks done", [m.tasks_done, m.tasks_total]) }}
            </span>
          </div>
          <p v-if="m.description" class="text-xs text-ink-gray-6 mt-1 whitespace-pre-line">
            {{ m.description }}
          </p>
        </button>
      </div>
    </div>
    <p v-else-if="!milestones.loading" class="text-sm text-ink-gray-5">
      {{ __("No milestones yet.") }}
    </p>

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
import { reactive, ref, watch } from "vue";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { __ } from "@/translation";
import LucidePlus from "~icons/lucide/plus";
import LucideCheck from "~icons/lucide/check";
import LucideFlag from "~icons/lucide/flag";
import LucideCalendar from "~icons/lucide/calendar";
import LucideEyeOff from "~icons/lucide/eye-off";

interface P {
  projectId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });
const emit = defineEmits(["changed"]);

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

// --- create / edit ---
const showDialog = ref(false);
const editing = ref<string | null>(null);
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
function openEdit(m: any) {
  editing.value = m.name;
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
</script>
