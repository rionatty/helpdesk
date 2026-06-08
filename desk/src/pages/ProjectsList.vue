<template>
  <div
    class="flex flex-col h-full"
    :class="isCustomerPortal && 'bg-customer-portal'"
  >
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideFolderKanban class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Projects") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <Button
          v-if="!isCustomerPortal"
          variant="solid"
          theme="gray"
          @click="openCreate"
        >
          <template #prefix><LucidePlus class="size-4" /></template>
          {{ __("New project") }}
        </Button>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-5 flex-1 overflow-y-auto"
    >
      <!-- Filters -->
      <div class="flex flex-wrap items-center gap-3">
        <Link
          v-if="!isCustomerPortal"
          class="form-control w-56"
          doctype="HD Customer"
          :placeholder="__('Filter by customer')"
          v-model="customerFilter"
          :hide-me="true"
        />
        <div class="flex items-center gap-1.5 flex-wrap">
          <button
            v-for="s in statusFilters"
            :key="s.value"
            type="button"
            class="px-3 py-1 rounded-full text-xs font-medium border transition-colors"
            :class="
              statusFilter === s.value
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'border-outline-gray-2 text-ink-gray-6 hover:border-outline-gray-3'
            "
            @click="statusFilter = s.value"
          >
            {{ s.label }}
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="projects.loading" class="flex flex-col gap-3">
        <div
          v-for="i in 4"
          :key="i"
          class="h-24 rounded-xl bg-surface-gray-2 animate-pulse"
        />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!filtered.length"
        class="executive-card flex flex-col items-center justify-center text-center py-14 gap-2"
      >
        <div
          class="size-12 rounded-full bg-surface-gray-2 flex items-center justify-center"
        >
          <LucideFolderKanban class="size-6 text-ink-gray-5" />
        </div>
        <p class="font-medium text-ink-gray-8">{{ __("No projects yet") }}</p>
        <p class="text-sm text-ink-gray-5">
          {{
            isCustomerPortal
              ? __("Your projects will appear here once we set them up.")
              : __("Create a project to start tracking an engagement.")
          }}
        </p>
      </div>

      <!-- Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          v-for="p in filtered"
          :key="p.name"
          type="button"
          class="executive-card executive-card-hover text-start p-5 flex flex-col gap-3"
          @click="open(p.name)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="text-base font-semibold text-ink-gray-9 truncate">
                {{ p.project_name }}
              </div>
              <div class="text-xs text-ink-gray-5 truncate">
                {{ p.customer }}
              </div>
            </div>
            <Badge
              :label="p.status"
              :theme="statusTheme(p.status)"
              variant="subtle"
            />
          </div>
          <div class="flex flex-col gap-1">
            <div class="flex items-center justify-between text-xs text-ink-gray-6">
              <span>{{ __("Progress") }}</span>
              <span class="font-medium">{{ p.progress || 0 }}%</span>
            </div>
            <div class="h-2 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-500"
                :style="{ width: (p.progress || 0) + '%' }"
              />
            </div>
          </div>
          <div
            v-if="p.end_date"
            class="text-xs text-ink-gray-5 flex items-center gap-1"
          >
            <LucideCalendar class="size-3.5" />
            {{ __("Target") }}: {{ p.end_date }}
          </div>
        </button>
      </div>
    </div>

    <!-- Create dialog (agent only) -->
    <Dialog
      v-if="!isCustomerPortal"
      v-model="showCreate"
      :options="{ title: __('New project'), size: 'xl' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <FormControl
            v-model="form.project_name"
            :label="__('Project name')"
            type="text"
          />
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-6">{{ __("Customer") }}</span>
              <Link doctype="HD Customer" v-model="form.customer" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-6">{{ __("Team") }}</span>
              <Link doctype="HD Team" v-model="form.team" :hide-me="true" />
            </div>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <FormControl
              v-model="form.status"
              :label="__('Status')"
              type="select"
              :options="statusOptions"
            />
            <FormControl
              v-model="form.start_date"
              :label="__('Start')"
              type="date"
            />
            <FormControl
              v-model="form.end_date"
              :label="__('Target end')"
              type="date"
            />
          </div>
          <FormControl
            v-model.number="form.progress"
            :label="__('Progress %')"
            type="number"
          />
          <FormControl
            v-model="form.description"
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
          @click="submitCreate"
        >
          {{ __("Create project") }}
        </Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import LucideFolderKanban from "~icons/lucide/folder-kanban";
import LucidePlus from "~icons/lucide/plus";
import LucideCalendar from "~icons/lucide/calendar";

const router = useRouter();

const STATUSES = ["Planned", "Active", "On Hold", "Completed", "Cancelled"];
const statusOptions = STATUSES.map((s) => ({ label: s, value: s }));
const statusFilters = [
  { value: "", label: __("All") },
  { value: "Active", label: __("Active") },
  { value: "On Hold", label: __("On Hold") },
  { value: "Completed", label: __("Completed") },
];
const statusFilter = ref("");
const customerFilter = ref("");

const projects = createResource({
  url: "helpdesk.api.project.get_projects",
  makeParams: () => ({ customer: customerFilter.value || undefined }),
  auto: true,
});
watch(customerFilter, () => projects.reload());

const filtered = computed(() => {
  const rows = projects.data || [];
  return statusFilter.value
    ? rows.filter((p: any) => p.status === statusFilter.value)
    : rows;
});

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

function open(name: string) {
  router.push({
    name: isCustomerPortal.value ? "ProjectCustomer" : "ProjectAgent",
    params: { projectId: name },
  });
}

// --- Create (agent) ---
const showCreate = ref(false);
const form = reactive({
  project_name: "",
  customer: "",
  team: "",
  status: "Planned",
  start_date: "",
  end_date: "",
  progress: 0,
  description: "",
});
function openCreate() {
  Object.assign(form, {
    project_name: "",
    customer: "",
    team: "",
    status: "Planned",
    start_date: "",
    end_date: "",
    progress: 0,
    description: "",
  });
  showCreate.value = true;
}
const createRes = createResource({
  url: "helpdesk.api.project.create_project",
  onSuccess: (name: string) => {
    showCreate.value = false;
    toast.success(__("Project created"));
    router.push({ name: "ProjectAgent", params: { projectId: name } });
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not create project")),
});
function submitCreate() {
  if (!form.project_name.trim() || !form.customer) {
    toast.error(__("Project name and customer are required"));
    return;
  }
  createRes.submit({ ...form });
}

usePageMeta(() => ({ title: __("Projects") }));
</script>
