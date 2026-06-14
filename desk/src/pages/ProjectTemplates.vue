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
                  "Milestone due dates are set relative to the project’s start when applied (start + “due after” days)."
                )
              }}
            </div>
          </div>

          <!-- Milestones + Tasks (unified accordion) -->
          <div class="executive-card p-5 flex flex-col gap-3">
            <!-- Section header -->
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

            <!-- Empty milestones state -->
            <p
              v-if="!editing.milestones.length"
              class="text-sm text-ink-gray-5"
            >
              {{ __("No milestones yet. Add one to start building your template.") }}
            </p>

            <!-- Milestone accordion list -->
            <div v-else class="flex flex-col gap-2">
              <div
                v-for="(m, mi) in editing.milestones"
                :key="m._id"
                class="rounded-lg border border-outline-gray-2 overflow-hidden"
              >
                <!-- Milestone header row -->
                <div
                  class="flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none hover:bg-surface-gray-1 transition-colors"
                  @click="toggleMilestone(m._id)"
                >
                  <LucideChevronDown
                    v-if="expandedMilestones.has(m._id)"
                    class="size-4 shrink-0 text-ink-gray-5"
                  />
                  <LucideChevronRight
                    v-else
                    class="size-4 shrink-0 text-ink-gray-5"
                  />
                  <input
                    v-model="m.title"
                    :placeholder="__('Milestone title')"
                    class="flex-1 min-w-0 text-sm font-medium text-ink-gray-9 bg-transparent focus:outline-none"
                    @click.stop
                  />
                  <!-- Info badges -->
                  <span class="hidden sm:inline text-[11px] text-ink-gray-5 shrink-0">
                    {{ (tasksByMilestone.get(m._id) ?? []).length }}
                    {{ __("tasks") }}
                  </span>
                  <span
                    v-if="m.due_after_days > 0"
                    class="hidden sm:inline text-[11px] bg-surface-gray-2 text-ink-gray-6 rounded px-1.5 py-0.5 shrink-0"
                  >
                    {{ __("Day {0}", [m.due_after_days]) }}
                  </span>
                  <span
                    v-if="!m.customer_visible"
                    class="hidden sm:inline-flex items-center gap-0.5 text-[11px] bg-surface-gray-2 text-ink-gray-6 rounded px-1.5 py-0.5 shrink-0"
                  >
                    <LucideEyeOff class="size-3" /> {{ __("Internal") }}
                  </span>
                  <!-- Add task shortcut -->
                  <button
                    type="button"
                    class="shrink-0 inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-50 transition-colors"
                    @click.stop="addTaskToMilestone(m._id)"
                  >
                    <LucidePlus class="size-3" />
                    <span class="hidden sm:inline">{{ __("Task") }}</span>
                  </button>
                  <!-- Delete milestone -->
                  <button
                    type="button"
                    class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
                    :aria-label="__('Remove milestone')"
                    @click.stop="removeMilestone(mi)"
                  >
                    <LucideTrash2 class="size-4" />
                  </button>
                </div>

                <!-- Expanded body -->
                <div
                  v-show="expandedMilestones.has(m._id)"
                  class="border-t border-outline-gray-2"
                >
                  <!-- Milestone details -->
                  <div class="px-3 pt-3 pb-2 bg-surface-gray-1 flex flex-col gap-2">
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

                  <!-- Task rows -->
                  <div
                    v-if="(tasksByMilestone.get(m._id) ?? []).length"
                    class="divide-y divide-outline-gray-2"
                  >
                    <div
                      v-for="t in tasksByMilestone.get(m._id)"
                      :key="editing.tasks.indexOf(t)"
                      class="px-3 py-2 flex flex-col gap-1.5 group/task bg-surface-white"
                    >
                      <div class="flex items-center gap-2">
                        <span class="text-ink-gray-3 text-xs shrink-0 select-none">•</span>
                        <input
                          v-model="t.subject"
                          :placeholder="__('Task subject')"
                          class="flex-1 min-w-0 text-sm text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                        />
                        <select v-model="t.status" class="tpl-sel">
                          <option v-for="s in TASK_STATUSES" :key="s" :value="s">{{ s }}</option>
                        </select>
                        <select v-model="t.priority" class="tpl-sel">
                          <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
                        </select>
                        <button
                          type="button"
                          class="opacity-0 group-hover/task:opacity-100 text-ink-gray-4 hover:text-ink-red-3 shrink-0 transition-opacity"
                          @click="removeTask(t)"
                        >
                          <LucideTrash2 class="size-3.5" />
                        </button>
                      </div>
                      <div class="flex items-center gap-3 pl-4 flex-wrap">
                        <select v-model="t.assigned_to" class="tpl-sel-sm">
                          <option :value="null">{{ __("Unassigned") }}</option>
                          <option
                            v-for="a in agentOptions"
                            :key="a.value"
                            :value="a.value"
                          >
                            {{ a.label }}
                          </option>
                        </select>
                        <label
                          class="flex items-center gap-1 text-[11px] text-ink-gray-6 cursor-pointer shrink-0"
                        >
                          <input v-model="t.is_internal" type="checkbox" />
                          <LucideEyeOff class="size-3" />
                          {{ __("Internal") }}
                        </label>
                        <input
                          v-model="t.description"
                          :placeholder="__('Note (optional)')"
                          class="flex-1 min-w-0 text-[11px] text-ink-gray-6 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                        />
                      </div>
                    </div>
                  </div>
                  <p v-else class="text-xs text-ink-gray-5 italic px-4 py-2 bg-surface-white">
                    {{ __("No tasks yet.") }}
                  </p>

                  <!-- Add task footer -->
                  <div class="border-t border-outline-gray-2 px-3 py-2 bg-surface-white">
                    <button
                      type="button"
                      class="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                      @click="addTaskToMilestone(m._id)"
                    >
                      <LucidePlus class="size-3" />
                      {{ __("Add task to this milestone") }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Unattached tasks section -->
            <div class="rounded-lg border border-dashed border-outline-gray-3">
              <!-- Unattached header -->
              <div
                class="flex items-center gap-2 px-3 py-2 cursor-pointer select-none hover:bg-surface-gray-1 transition-colors rounded-lg"
                @click="showUnattached = !showUnattached"
              >
                <LucideChevronDown
                  v-if="showUnattached"
                  class="size-4 shrink-0 text-ink-gray-5"
                />
                <LucideChevronRight
                  v-else
                  class="size-4 shrink-0 text-ink-gray-5"
                />
                <span class="text-xs font-medium text-ink-gray-7 flex-1">
                  {{ __("Unattached tasks") }}
                </span>
                <span class="text-xs text-ink-gray-5">
                  · {{ unattachedTasks.length }}
                </span>
                <button
                  type="button"
                  class="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 px-1.5 py-0.5 rounded hover:bg-blue-50 transition-colors"
                  @click.stop="addUnattachedTask"
                >
                  <LucidePlus class="size-3" />
                  {{ __("Add") }}
                </button>
              </div>

              <!-- Unattached task rows -->
              <div
                v-show="showUnattached && unattachedTasks.length"
                class="border-t border-outline-gray-2 divide-y divide-outline-gray-2 rounded-b-lg overflow-hidden"
              >
                <div
                  v-for="t in unattachedTasks"
                  :key="editing.tasks.indexOf(t)"
                  class="px-3 py-2 flex flex-col gap-1.5 group/task bg-surface-white"
                >
                  <div class="flex items-center gap-2">
                    <span class="text-ink-gray-3 text-xs shrink-0 select-none">•</span>
                    <input
                      v-model="t.subject"
                      :placeholder="__('Task subject')"
                      class="flex-1 min-w-0 text-sm text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                    />
                    <select v-model="t.status" class="tpl-sel">
                      <option v-for="s in TASK_STATUSES" :key="s" :value="s">{{ s }}</option>
                    </select>
                    <select v-model="t.priority" class="tpl-sel">
                      <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
                    </select>
                    <button
                      type="button"
                      class="opacity-0 group-hover/task:opacity-100 text-ink-gray-4 hover:text-ink-red-3 shrink-0 transition-opacity"
                      @click="removeTask(t)"
                    >
                      <LucideTrash2 class="size-3.5" />
                    </button>
                  </div>
                  <div class="flex items-center gap-3 pl-4 flex-wrap">
                    <select v-model="t.assigned_to" class="tpl-sel-sm">
                      <option :value="null">{{ __("Unassigned") }}</option>
                      <option
                        v-for="a in agentOptions"
                        :key="a.value"
                        :value="a.value"
                      >
                        {{ a.label }}
                      </option>
                    </select>
                    <label
                      class="flex items-center gap-1 text-[11px] text-ink-gray-6 cursor-pointer shrink-0"
                    >
                      <input v-model="t.is_internal" type="checkbox" />
                      <LucideEyeOff class="size-3" />
                      {{ __("Internal") }}
                    </label>
                    <input
                      v-model="t.description"
                      :placeholder="__('Note (optional)')"
                      class="flex-1 min-w-0 text-[11px] text-ink-gray-6 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
                    />
                  </div>
                </div>
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
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideEyeOff from "~icons/lucide/eye-off";

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

// Accordion state
const expandedMilestones: Set<number> = reactive(new Set());
const showUnattached = ref(false);

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
    expandedMilestones.clear();
    showUnattached.value = false;
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

// Tasks grouped by milestone _id (reactive — updates when editing.tasks changes)
const tasksByMilestone = computed(() => {
  const map = new Map<number, any[]>();
  for (const t of editing.tasks) {
    if (t._milestone_id != null) {
      if (!map.has(t._milestone_id)) map.set(t._milestone_id, []);
      map.get(t._milestone_id)!.push(t);
    }
  }
  return map;
});

const unattachedTasks = computed(() =>
  editing.tasks.filter((t: any) => t._milestone_id == null)
);

function select(name: string) {
  selectedName.value = name;
  detail.reload();
}

function toggleMilestone(id: number) {
  if (expandedMilestones.has(id)) expandedMilestones.delete(id);
  else expandedMilestones.add(id);
}

function addMilestone() {
  const _id = ++midCounter;
  editing.milestones.push({
    _id,
    title: "",
    sequence: editing.milestones.length + 1,
    due_after_days: 0,
    customer_visible: true,
    description: "",
  });
  expandedMilestones.add(_id); // auto-expand so the user can fill details immediately
}

function removeMilestone(i: number) {
  const m = editing.milestones[i];
  // Unattach tasks rather than silently deleting them
  for (const t of editing.tasks) {
    if (t._milestone_id === m._id) t._milestone_id = null;
  }
  expandedMilestones.delete(m._id);
  editing.milestones.splice(i, 1);
}

function addTaskToMilestone(milestoneId: number) {
  editing.tasks.push({
    subject: "",
    _milestone_id: milestoneId,
    status: "To Do",
    priority: "Medium",
    assigned_to: null,
    is_internal: false,
    description: "",
  });
  expandedMilestones.add(milestoneId);
}

function addUnattachedTask() {
  editing.tasks.push({
    subject: "",
    _milestone_id: null,
    status: "To Do",
    priority: "Medium",
    assigned_to: null,
    is_internal: false,
    description: "",
  });
  showUnattached.value = true;
}

function removeTask(task: any) {
  const idx = editing.tasks.indexOf(task);
  if (idx >= 0) editing.tasks.splice(idx, 1);
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

<style scoped>
.tpl-sel {
  @apply text-xs rounded border border-outline-gray-2 bg-surface-white px-1.5 py-0.5 text-ink-gray-7 focus:outline-none focus:border-blue-400 shrink-0;
}
.tpl-sel-sm {
  @apply text-[11px] rounded border border-outline-gray-2 bg-surface-white px-1.5 py-0.5 text-ink-gray-6 focus:outline-none focus:border-blue-400 shrink-0;
}
</style>
