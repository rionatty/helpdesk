<template>
  <div
    class="flex flex-col h-full"
    :class="isCustomerPortal && 'bg-customer-portal'"
  >
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <div v-if="editable && resource.data" class="flex items-center gap-2">
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
      </template>
    </LayoutHeader>

    <div
      v-if="resource.data"
      class="w-full max-w-screen-lg mx-auto px-4 md:px-6 py-6 flex flex-col gap-5 flex-1 overflow-y-auto"
    >
      <!-- Header / details -->
      <div class="executive-card p-6 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <input
              v-if="editable"
              v-model="form.project_name"
              class="w-full text-2xl font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
            />
            <h1 v-else class="text-2xl font-semibold text-ink-gray-9">
              {{ resource.data.project_name }}
            </h1>
            <div class="text-sm text-ink-gray-5 mt-0.5">
              {{ resource.data.customer }}
            </div>
          </div>
          <select
            v-if="editable"
            v-model="form.status"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          >
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
          <Badge
            v-else
            :label="resource.data.status"
            :theme="statusTheme(resource.data.status)"
            variant="subtle"
          />
        </div>

        <!-- Progress -->
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center justify-between text-xs text-ink-gray-6">
            <span>{{ __("Progress") }}</span>
            <span v-if="!editable" class="font-medium">
              {{ resource.data.progress || 0 }}%
            </span>
            <input
              v-else
              v-model.number="form.progress"
              type="number"
              min="0"
              max="100"
              class="w-16 text-xs rounded border border-outline-gray-2 px-2 py-0.5 text-end focus:outline-none focus:border-blue-400"
            />
          </div>
          <div class="h-2.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
            <div
              class="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-500"
              :style="{ width: progressPct + '%' }"
            />
          </div>
        </div>

        <!-- Meta grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Team") }}</span>
            <Link v-if="editable" doctype="HD Team" v-model="form.team" :hide-me="true" />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.team || "—" }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Start date") }}</span>
            <input
              v-if="editable"
              v-model="form.start_date"
              type="date"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.start_date || "—" }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Target end") }}</span>
            <input
              v-if="editable"
              v-model="form.end_date"
              type="date"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.end_date || "—" }}
            </span>
          </div>
        </div>

        <!-- Description -->
        <div class="flex flex-col gap-1 pt-1">
          <span class="text-xs text-ink-gray-5">{{ __("Description") }}</span>
          <textarea
            v-if="editable"
            v-model="form.description"
            rows="3"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
          />
          <p v-else class="text-sm text-ink-gray-8 whitespace-pre-line">
            {{ resource.data.description || __("No description.") }}
          </p>
        </div>
      </div>

      <!-- Linked tickets -->
      <div class="executive-card p-5 flex flex-col gap-2">
        <div class="text-sm font-semibold text-ink-gray-8">
          {{ __("Linked tickets") }}
        </div>
        <div
          v-if="resource.data.tickets?.length"
          class="flex flex-col divide-y divide-outline-gray-1"
        >
          <button
            v-for="t in resource.data.tickets"
            :key="t.name"
            type="button"
            class="flex items-center justify-between gap-3 py-2 px-1 text-start rounded hover:bg-surface-menu-bar"
            @click="openTicket(t.name)"
          >
            <span class="text-sm text-ink-gray-8 truncate">
              #{{ t.name }} · {{ t.subject }}
            </span>
            <span class="text-xs text-ink-gray-5 shrink-0">{{ t.status }}</span>
          </button>
        </div>
        <p v-else class="text-sm text-ink-gray-5">
          {{ __("No tickets linked to this project yet.") }}
        </p>
      </div>

      <!-- Tasks -->
      <div class="executive-card p-5">
        <TaskBoard :project-id="projectId" :editable="editable" />
      </div>

      <!-- Upcoming features -->
      <div class="executive-card p-5 flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <div class="text-sm font-semibold text-ink-gray-8">
            {{ __("Upcoming features") }}
          </div>
          <Button
            v-if="editable"
            variant="subtle"
            size="sm"
            @click="openTagDialog"
          >
            <template #prefix><LucideTags class="size-3.5" /></template>
            {{ __("Tag features") }}
          </Button>
        </div>
        <div
          v-if="resource.data.features?.length"
          class="flex flex-col gap-2"
        >
          <div
            v-for="f in resource.data.features"
            :key="f.name"
            class="flex items-center gap-2"
          >
            <span class="size-2 rounded-full" :class="featureDot(f.status)" />
            <span class="text-sm text-ink-gray-8 flex-1 truncate">
              {{ f.feature_title }}
            </span>
            <span class="text-xs text-ink-gray-5 truncate">{{ f.addon }}</span>
            <Badge
              :label="f.status"
              :theme="featureTheme(f.status)"
              variant="subtle"
            />
          </div>
        </div>
        <p v-else class="text-sm text-ink-gray-5">
          {{ __("No features tagged to this project yet.") }}
        </p>
      </div>

      <!-- Discussion -->
      <div class="executive-card p-5">
        <ProjectComments :project-id="projectId" />
      </div>
    </div>

    <!-- Tag features dialog (agent only) -->
    <Dialog
      v-if="editable"
      v-model="showTag"
      :options="{ title: __('Tag features to this project'), size: 'lg' }"
    >
      <template #body-content>
        <div v-if="taggable.loading" class="py-6 text-center text-sm text-ink-gray-5">
          {{ __("Loading…") }}
        </div>
        <div
          v-else-if="!taggable.data?.length"
          class="py-6 text-center text-sm text-ink-gray-5"
        >
          {{ __("No add-on features found for this customer.") }}
        </div>
        <div v-else class="flex flex-col gap-1 max-h-96 overflow-y-auto">
          <label
            v-for="f in taggable.data"
            :key="f.name"
            class="flex items-center gap-2.5 px-2 py-2 rounded hover:bg-surface-menu-bar cursor-pointer"
          >
            <input
              type="checkbox"
              :checked="f.project === projectId"
              :disabled="!!f.project && f.project !== projectId"
              @change="toggleTag(f)"
            />
            <span class="text-sm text-ink-gray-8 flex-1">
              {{ f.feature_title }}
            </span>
            <span class="text-xs text-ink-gray-5">{{ f.addon }}</span>
            <span
              v-if="f.project && f.project !== projectId"
              class="text-[11px] text-ink-gray-4"
            >
              {{ __("on {0}", [f.project]) }}
            </span>
          </label>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, ref } from "vue";
import {
  Badge,
  Breadcrumbs,
  Button,
  Dialog,
  createResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import ProjectComments from "@/components/ProjectComments.vue";
import TaskBoard from "@/components/TaskBoard.vue";
import LucideTags from "~icons/lucide/tags";
import { globalStore } from "@/stores/globalStore";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";

interface P {
  projectId: string;
}
const props = defineProps<P>();
const router = useRouter();
const { $dialog } = globalStore();

const STATUSES = ["Planned", "Active", "On Hold", "Completed", "Cancelled"];
const editable = computed(() => !isCustomerPortal.value);
const progressPct = computed(
  () => (editable.value ? form.progress : resource.data?.progress) || 0
);

const form = reactive({
  project_name: "",
  status: "Planned",
  team: "",
  start_date: "",
  end_date: "",
  progress: 0,
  description: "",
});

const resource = createResource({
  url: "helpdesk.api.project.get_project",
  makeParams: () => ({ name: props.projectId }),
  auto: true,
  onSuccess: (d: any) => {
    form.project_name = d.project_name || "";
    form.status = d.status || "Planned";
    form.team = d.team || "";
    form.start_date = d.start_date || "";
    form.end_date = d.end_date || "";
    form.progress = d.progress || 0;
    form.description = d.description || "";
  },
  onError: () => {
    toast.error(__("Project not found"));
    router.replace({ name: isCustomerPortal.value ? "ProjectsCustomer" : "ProjectsAgent" });
  },
});

const breadcrumbs = computed(() => [
  {
    label: __("Projects"),
    route: { name: isCustomerPortal.value ? "ProjectsCustomer" : "ProjectsAgent" },
  },
  { label: resource.data?.project_name || props.projectId },
]);

function statusTheme(status: string) {
  return (
    {
      Planned: "gray",
      Active: "blue",
      "On Hold": "orange",
      Completed: "green",
      Cancelled: "red",
    }[status] || "gray"
  );
}

const saveRes = createResource({
  url: "helpdesk.api.project.update_project",
  onSuccess: () => {
    toast.success(__("Saved"));
    resource.reload();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not save")),
});
function save() {
  saveRes.submit({ name: props.projectId, ...form });
}

const deleteRes = createResource({
  url: "helpdesk.api.project.delete_project",
  onSuccess: () => {
    toast.success(__("Project deleted"));
    router.replace({ name: "ProjectsAgent" });
  },
});
function confirmDelete() {
  $dialog({
    title: __("Delete project"),
    message: __("This will permanently delete the project and its comments."),
    actions: [
      {
        label: __("Delete"),
        theme: "red",
        variant: "solid",
        onClick: (close: Function) => {
          deleteRes.submit({ name: props.projectId });
          close();
        },
      },
    ],
  });
}

function openTicket(name: string) {
  router.push({
    name: isCustomerPortal.value ? "TicketCustomer" : "TicketAgent",
    params: { ticketId: name },
  });
}

// --- Tag add-on features to this project (agent) ---
const showTag = ref(false);
const taggable = createResource({
  url: "helpdesk.api.project.get_taggable_features",
  makeParams: () => ({ project: props.projectId }),
});
function openTagDialog() {
  showTag.value = true;
  taggable.reload();
}
const tagRes = createResource({
  url: "helpdesk.api.addon.update_feature",
  onSuccess: () => {
    taggable.reload();
    resource.reload();
  },
});
function toggleTag(f: any) {
  const tagged = f.project === props.projectId;
  tagRes.submit({ name: f.name, project: tagged ? "" : props.projectId });
}
function featureDot(status: string) {
  return (
    {
      Planned: "bg-ink-gray-4",
      "In Progress": "bg-blue-500",
      Released: "bg-green-500",
      Deprecated: "bg-amber-500",
    }[status] || "bg-ink-gray-4"
  );
}
function featureTheme(status: string) {
  return (
    {
      Planned: "gray",
      "In Progress": "blue",
      Released: "green",
      Deprecated: "orange",
    }[status] || "gray"
  );
}

usePageMeta(() => ({
  title: resource.data?.project_name || __("Project"),
}));
</script>
