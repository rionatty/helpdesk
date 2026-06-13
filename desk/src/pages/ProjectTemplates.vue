<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideLayoutTemplate class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Project templates") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <Button variant="solid" theme="gray" @click="openNew">
          <template #prefix><LucidePlus class="size-4" /></template>
          {{ __("New template") }}
        </Button>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-xl mx-auto px-4 md:px-6 lg:px-8 py-6 grid grid-cols-1 md:grid-cols-[300px_1fr] gap-5 flex-1 overflow-y-auto md:overflow-hidden"
    >
      <!-- Template list -->
      <div class="flex flex-col gap-2 md:overflow-y-auto md:pr-1">
        <div v-if="list.loading" class="flex flex-col gap-2">
          <div
            v-for="i in 4"
            :key="i"
            class="h-16 rounded-xl bg-surface-gray-2 animate-pulse"
          />
        </div>
        <div
          v-else-if="!list.data?.length"
          class="executive-card p-5 text-center text-sm text-ink-gray-5"
        >
          {{ __("No templates yet. Create one to get started.") }}
        </div>
        <button
          v-for="t in list.data"
          :key="t.name"
          type="button"
          class="executive-card text-start p-4 flex flex-col gap-1.5 transition-colors"
          :class="
            t.name === selectedName
              ? 'ring-2 ring-blue-500'
              : 'executive-card-hover'
          "
          @click="select(t.name)"
        >
          <div class="text-sm font-semibold text-ink-gray-9 truncate">
            {{ t.template_name }}
          </div>
          <div class="flex items-center gap-2 text-xs text-ink-gray-5">
            <span class="inline-flex items-center gap-1">
              <LucideFlag class="size-3" /> {{ t.milestone_count }}
            </span>
            <span class="inline-flex items-center gap-1">
              <LucideListChecks class="size-3" /> {{ t.task_count }}
            </span>
          </div>
        </button>
      </div>

      <!-- Editor -->
      <div class="md:overflow-y-auto md:pr-1">
        <!-- Empty state -->
        <div
          v-if="!selectedName"
          class="executive-card flex flex-col items-center justify-center text-center py-16 gap-2"
        >
          <div
            class="size-12 rounded-full bg-surface-gray-2 flex items-center justify-center"
          >
            <LucideLayoutTemplate class="size-6 text-ink-gray-5" />
          </div>
          <p class="font-medium text-ink-gray-8">
            {{ __("Select a template to edit") }}
          </p>
          <p class="text-sm text-ink-gray-5 max-w-sm">
            {{
              __(
                "Templates define the milestones and tasks that get stamped out when you create a project from them."
              )
            }}
          </p>
        </div>

        <div v-else-if="detail.loading" class="executive-card p-6">
          <div class="h-40 rounded-lg bg-surface-gray-2 animate-pulse" />
        </div>

        <div v-else class="flex flex-col gap-5">
          <!-- Header card -->
          <div class="executive-card p-5 flex flex-col gap-4">
            <div class="flex items-start gap-3">
              <input
                v-model="editing.template_name"
                :placeholder="__('Template name')"
                class="flex-1 min-w-0 text-xl font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
              />
              <div class="flex items-center gap-2 shrink-0">
                <Button
                  theme="red"
                  variant="ghost"
                  :label="__('Delete')"
                  @click="confirmDelete"
                />
                <Button
                  theme="blue"
                  variant="solid"
                  :label="__('Save')"
                  :loading="saveRes.loading"
                  @click="save"
                />
              </div>
            </div>
            <textarea
              v-model="editing.description"
              rows="2"
              :placeholder="__('What is this template for?')"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
            />
            <div class="text-xs text-ink-gray-5">
              {{
                __(
                  "Milestone due dates are set relative to the project's start when applied (start + “due after” days)."
                )
              }}
            </div>
          </div>

          <!-- Milestones -->
          <div class="executive-card p-5 flex flex-col gap-3">
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
                <span class="text-xs text-ink-gray-5">
                  · {{ editing.milestones.length }}
                </span>
              </div>
              <Button variant="subtle" size="sm" @click="addMilestone">
                <template #prefix><LucidePlus class="size-3.5" /></template>
                {{ __("Add milestone") }}
              </Button>
            </div>

            <p
              v-if="!editing.milestones.length"
              class="text-sm text-ink-gray-5"
            >
              {{ __("No milestones yet.") }}
            </p>
            <div v-else class="flex flex-col gap-2">
              <div
                v-for="(m, i) in editing.milestones"
                :key="i"
                class="rounded-lg border border-outline-gray-2 p-3 flex flex-col gap-2"
              >
                <div class="flex items-center gap-2">
                  <input
                    v-model="m.title"
                    :placeholder="__('Milestone title')"
                    class="flex-1 min-w-0 text-sm font-medium text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                  />
                  <button
                    type="button"
                    class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
                    :aria-label="__('Remove milestone')"
                    @click="removeMilestone(i)"
                  >
                    <LucideTrash2 class="size-4" />
                  </button>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 items-end">
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">{{ __("Order") }}</span>
                    <input
                      v-model.number="m.sequence"
                      type="number"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                    />
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">
                      {{ __("Due after (days)") }}
                    </span>
                    <input
                      v-model.number="m.due_after_days"
                      type="number"
                      min="0"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                    />
                  </label>
                  <label
                    class="flex items-center gap-2 text-xs text-ink-gray-7 cursor-pointer sm:col-span-2"
                  >
                    <input v-model="m.customer_visible" type="checkbox" />
                    {{ __("Visible to the customer") }}
                  </label>
                </div>
                <input
                  v-model="m.description"
                  :placeholder="__('Description (optional)')"
                  class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                />
              </div>
            </div>
          </div>

          <!-- Tasks -->
          <div class="executive-card p-5 flex flex-col gap-3">
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
                <span class="text-xs text-ink-gray-5">
                  · {{ editing.tasks.length }}
                </span>
              </div>
              <Button variant="subtle" size="sm" @click="addTask">
                <template #prefix><LucidePlus class="size-3.5" /></template>
                {{ __("Add task") }}
              </Button>
            </div>

            <p v-if="!editing.tasks.length" class="text-sm text-ink-gray-5">
              {{ __("No tasks yet.") }}
            </p>
            <div v-else class="flex flex-col gap-2">
              <div
                v-for="(t, i) in editing.tasks"
                :key="i"
                class="rounded-lg border border-outline-gray-2 p-3 flex flex-col gap-2"
              >
                <div class="flex items-center gap-2">
                  <input
                    v-model="t.subject"
                    :placeholder="__('Task subject')"
                    class="flex-1 min-w-0 text-sm font-medium text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                  />
                  <button
                    type="button"
                    class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
                    :aria-label="__('Remove task')"
                    @click="removeTask(i)"
                  >
                    <LucideTrash2 class="size-4" />
                  </button>
                </div>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">{{ __("Milestone") }}</span>
                    <select
                      v-model="t._milestone_id"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                    >
                      <option :value="null">{{ __("Unattached") }}</option>
                      <option
                        v-for="opt in milestoneSelectOptions"
                        :key="opt.id"
                        :value="opt.id"
                      >
                        {{ opt.label }}
                      </option>
                    </select>
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">{{ __("Status") }}</span>
                    <select
                      v-model="t.status"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                    >
                      <option v-for="s in TASK_STATUSES" :key="s" :value="s">
                        {{ s }}
                      </option>
                    </select>
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">{{ __("Priority") }}</span>
                    <select
                      v-model="t.priority"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                    >
                      <option v-for="p in PRIORITIES" :key="p" :value="p">
                        {{ p }}
                      </option>
                    </select>
                  </label>
                  <label class="flex flex-col gap-1">
                    <span class="text-[11px] text-ink-gray-5">{{ __("Assignee") }}</span>
                    <select
                      v-model="t.assigned_to"
                      class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                    >
                      <option :value="null">{{ __("Unassigned") }}</option>
                      <option
                        v-for="a in agentOptions"
                        :key="a.value"
                        :value="a.value"
                      >
                        {{ a.label }}
                      </option>
                    </select>
                  </label>
                </div>
                <label
                  class="flex items-center gap-2 text-xs text-ink-gray-7 cursor-pointer"
                >
                  <input v-model="t.is_internal" type="checkbox" />
                  {{ __("Internal only — hidden from the customer portal") }}
                </label>
                <input
                  v-model="t.description"
                  :placeholder="__('Description (optional)')"
                  class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 focus:outline-none focus:border-blue-400"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- New template dialog -->
    <Dialog
      v-model="showNew"
      :options="{ title: __('New template'), size: 'md' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <FormControl
            v-model="newForm.template_name"
            :label="__('Template name')"
            type="text"
            :placeholder="__('e.g. ERP Implementation')"
          />
          <FormControl
            v-model="newForm.description"
            :label="__('Description')"
            type="textarea"
          />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          theme="blue"
          class="w-full"
          :loading="createRes.loading"
          @click="submitNew"
        >
          {{ __("Create template") }}
        </Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import {
  Button,
  Dialog,
  FormControl,
  createResource,
  createListResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { LayoutHeader } from "@/components";
import { globalStore } from "@/stores/globalStore";
import { __ } from "@/translation";
import LucideLayoutTemplate from "~icons/lucide/layout-template";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideFlag from "~icons/lucide/flag";
import LucideListChecks from "~icons/lucide/list-checks";

const { $dialog } = globalStore();

const TASK_STATUSES = ["To Do", "In Progress", "Done", "Blocked"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];

const selectedName = ref("");
const editing = reactive<{
  template_name: string;
  description: string;
  milestones: any[];
  tasks: any[];
}>({
  template_name: "",
  description: "",
  milestones: [],
  tasks: [],
});

const list = createResource({
  url: "helpdesk.api.project_template.get_templates",
  auto: true,
});

// Tasks reference their milestone by a stable synthetic id (not the title
// string), so renaming a milestone follows the task and removing one cleanly
// unattaches it. The title is resolved back from the id only at save time.
let midCounter = 0;

const detail = createResource({
  url: "helpdesk.api.project_template.get_template",
  makeParams: () => ({ name: selectedName.value }),
  onSuccess: (d: any) => {
    editing.template_name = d.template_name || "";
    editing.description = d.description || "";
    const titleToId: Record<string, number> = {};
    editing.milestones = (d.milestones || []).map((m: any) => {
      const _id = ++midCounter;
      const title = (m.title || "").trim();
      if (title) titleToId[title] = _id;
      return { ...m, _id, customer_visible: !!m.customer_visible };
    });
    editing.tasks = (d.tasks || []).map((t: any) => ({
      ...t,
      is_internal: !!t.is_internal,
      assigned_to: t.assigned_to || null,
      _milestone_id: titleToId[(t.milestone_title || "").trim()] ?? null,
    }));
  },
});

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

const milestoneSelectOptions = computed(() =>
  editing.milestones.map((m: any) => ({
    id: m._id,
    label: (m.title || "").trim() || __("(untitled milestone)"),
  }))
);

function select(name: string) {
  selectedName.value = name;
  detail.reload();
}

function addMilestone() {
  editing.milestones.push({
    _id: ++midCounter,
    title: "",
    sequence: editing.milestones.length + 1,
    due_after_days: 0,
    customer_visible: true,
    description: "",
  });
}
function removeMilestone(i: number) {
  editing.milestones.splice(i, 1);
}
function addTask() {
  editing.tasks.push({
    subject: "",
    _milestone_id: null,
    status: "To Do",
    priority: "Medium",
    assigned_to: null,
    is_internal: false,
    description: "",
  });
}
function removeTask(i: number) {
  editing.tasks.splice(i, 1);
}

const saveRes = createResource({
  url: "helpdesk.api.project_template.update_template",
  onSuccess: (name: string) => {
    toast.success(__("Template saved"));
    if (name !== selectedName.value) selectedName.value = name;
    list.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save template")),
});
function save() {
  if (!editing.template_name.trim()) {
    toast.error(__("Template name is required"));
    return;
  }
  const idToTitle: Record<number, string> = {};
  editing.milestones.forEach((m: any) => {
    idToTitle[m._id] = (m.title || "").trim();
  });
  saveRes.submit({
    name: selectedName.value,
    template_name: editing.template_name.trim(),
    description: editing.description || "",
    milestones: JSON.stringify(
      editing.milestones.map((m: any) => ({
        title: m.title,
        sequence: m.sequence,
        due_after_days: m.due_after_days,
        customer_visible: m.customer_visible ? 1 : 0,
        description: m.description,
      }))
    ),
    tasks: JSON.stringify(
      editing.tasks.map((t: any) => ({
        subject: t.subject,
        milestone_title:
          t._milestone_id != null ? idToTitle[t._milestone_id] || "" : "",
        status: t.status,
        priority: t.priority,
        assigned_to: t.assigned_to,
        is_internal: t.is_internal ? 1 : 0,
        description: t.description,
      }))
    ),
  });
}

const deleteRes = createResource({
  url: "helpdesk.api.project_template.delete_template",
  onSuccess: () => {
    toast.success(__("Template deleted"));
    selectedName.value = "";
    list.reload();
  },
});
function confirmDelete() {
  $dialog({
    title: __("Delete template"),
    message: __("This permanently deletes the template. Projects already created from it are not affected."),
    actions: [
      {
        label: __("Delete"),
        theme: "red",
        variant: "solid",
        onClick: (close: Function) => {
          deleteRes.submit({ name: selectedName.value });
          close();
        },
      },
    ],
  });
}

// --- New template ---
const showNew = ref(false);
const newForm = reactive({ template_name: "", description: "" });
function openNew() {
  newForm.template_name = "";
  newForm.description = "";
  showNew.value = true;
}
const createRes = createResource({
  url: "helpdesk.api.project_template.create_template",
  onSuccess: (name: string) => {
    showNew.value = false;
    toast.success(__("Template created"));
    list.reload();
    select(name);
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not create template")),
});
function submitNew() {
  if (!newForm.template_name.trim()) {
    toast.error(__("Template name is required"));
    return;
  }
  createRes.submit({
    template_name: newForm.template_name.trim(),
    description: newForm.description || undefined,
  });
}

usePageMeta(() => ({ title: __("Project templates") }));
</script>
