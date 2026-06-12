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
        <div class="flex items-center gap-2">
          <Button
            v-if="resource.data && (!isInternal || editable)"
            theme="blue"
            variant="subtle"
            :label="__('New ticket')"
            @click="newTicket"
          >
            <template #prefix><LucideTicket class="size-4" /></template>
          </Button>
          <template v-if="editable && resource.data">
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
          </template>
        </div>
      </template>
    </LayoutHeader>

    <div
      v-if="resource.data"
      class="w-full max-w-screen-lg mx-auto px-4 md:px-6 py-6 flex flex-col gap-5 flex-1 overflow-y-auto"
    >
      <!-- Header / details -->
      <div class="executive-card overflow-hidden">
        <div class="h-1" :class="statusAccent" />
        <div class="p-6 flex flex-col gap-5">
          <!-- Title row -->
          <div class="flex items-start justify-between gap-3 flex-wrap">
            <div class="min-w-0 flex-1">
              <input
                v-if="editable"
                v-model="form.project_name"
                class="w-full text-2xl font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
              />
              <h1 v-else class="text-2xl font-semibold text-ink-gray-9">
                {{ resource.data.project_name }}
              </h1>
              <!-- Identity chips -->
              <div class="flex items-center gap-1.5 mt-2 flex-wrap">
                <span
                  v-if="isInternal"
                  class="meta-chip bg-surface-gray-2 text-ink-gray-6"
                >
                  <LucideEyeOff class="size-3" /> {{ __("Internal project") }}
                </span>
                <span
                  v-else-if="resource.data.customer"
                  class="meta-chip bg-blue-50 text-blue-700"
                >
                  <LucideBuilding2 class="size-3" />
                  {{ resource.data.customer }}
                </span>
                <span
                  v-if="resource.data.lead_name || resource.data.lead"
                  class="meta-chip bg-surface-gray-2 text-ink-gray-6"
                >
                  <LucideUserRound class="size-3" />
                  {{ resource.data.lead_name || resource.data.lead }}
                </span>
                <span
                  v-if="resource.data.team"
                  class="meta-chip bg-surface-gray-2 text-ink-gray-6"
                >
                  <LucideUsers class="size-3" /> {{ resource.data.team }}
                </span>
                <span
                  class="meta-chip"
                  :class="priorityChip(resource.data.priority)"
                >
                  <LucideFlag class="size-3" />
                  {{ __(resource.data.priority || "Medium") }}
                </span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <select
                v-if="editable"
                v-model="form.project_type"
                class="text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              >
                <option value="Customer">{{ __("Customer") }}</option>
                <option value="Internal">{{ __("Internal") }}</option>
              </select>
              <select
                v-if="editable"
                v-model="form.status"
                class="text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
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
          </div>

          <!-- Stat tiles -->
          <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <!-- Progress -->
            <div class="stat-tile">
              <div class="flex items-center justify-between">
                <span class="text-xs text-ink-gray-5">{{ __("Progress") }}</span>
                <LucideTrendingUp class="size-3.5 text-blue-500" />
              </div>
              <div class="text-xl font-semibold text-ink-gray-9">
                {{ progressPct }}%
              </div>
              <input
                v-if="editable"
                v-model.number="form.progress"
                type="range"
                min="0"
                max="100"
                class="w-full h-1.5 accent-blue-600 cursor-pointer"
              />
              <div
                v-else
                class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden"
              >
                <div
                  class="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all duration-500"
                  :style="{ width: progressPct + '%' }"
                />
              </div>
            </div>
            <!-- Milestones -->
            <div class="stat-tile">
              <div class="flex items-center justify-between">
                <span class="text-xs text-ink-gray-5">{{ __("Milestones") }}</span>
                <LucideFlag class="size-3.5 text-violet-500" />
              </div>
              <div class="text-xl font-semibold text-ink-gray-9">
                {{ milestoneStats.done
                }}<span class="text-sm font-normal text-ink-gray-5">
                  / {{ milestoneStats.total }}</span
                >
              </div>
              <div class="text-[11px] text-ink-gray-5">{{ __("completed") }}</div>
            </div>
            <!-- Tasks -->
            <div class="stat-tile">
              <div class="flex items-center justify-between">
                <span class="text-xs text-ink-gray-5">{{ __("Tasks") }}</span>
                <LucideListChecks class="size-3.5 text-green-600" />
              </div>
              <div class="text-xl font-semibold text-ink-gray-9">
                {{ taskStats.done
                }}<span class="text-sm font-normal text-ink-gray-5">
                  / {{ taskStats.total }}</span
                >
              </div>
              <div class="text-[11px] text-ink-gray-5">{{ __("done") }}</div>
            </div>
            <!-- Timeline -->
            <div class="stat-tile">
              <div class="flex items-center justify-between">
                <span class="text-xs text-ink-gray-5">{{ __("Timeline") }}</span>
                <LucideCalendarRange class="size-3.5 text-amber-500" />
              </div>
              <div
                class="text-base font-semibold leading-7"
                :class="timeline.overdue ? 'text-red-600' : 'text-ink-gray-9'"
              >
                {{ timeline.headline }}
              </div>
              <div class="text-[11px] text-ink-gray-5">{{ timeline.range }}</div>
            </div>
          </div>

          <!-- Meta grid (agent editing) -->
          <div v-if="editable" class="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
            <div
              v-if="form.project_type === 'Customer'"
              class="flex flex-col gap-1"
            >
              <span class="text-xs text-ink-gray-5">{{ __("Customer") }}</span>
              <Link doctype="HD Customer" v-model="form.customer" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Team") }}</span>
              <Link doctype="HD Team" v-model="form.team" :hide-me="true" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Project lead") }}</span>
              <Link doctype="HD Agent" v-model="form.lead" :hide-me="true" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Priority") }}</span>
              <select
                v-model="form.priority"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              >
                <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Start date") }}</span>
              <input
                v-model="form.start_date"
                type="date"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Target end") }}</span>
              <input
                v-model="form.end_date"
                type="date"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
              />
            </div>
          </div>

          <!-- Description -->
          <div
            v-if="editable || resource.data.description"
            class="flex flex-col gap-1"
          >
            <span class="text-xs text-ink-gray-5">{{ __("Description") }}</span>
            <textarea
              v-if="editable"
              v-model="form.description"
              rows="3"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
            />
            <p v-else class="text-sm text-ink-gray-8 whitespace-pre-line">
              {{ resource.data.description }}
            </p>
          </div>
        </div>
      </div>

      <!-- Milestones -->
      <div class="executive-card p-5">
        <ProjectMilestones
          ref="milestonesRef"
          :project-id="projectId"
          :editable="editable"
          @changed="taskBoardRef?.refreshMilestones()"
        />
      </div>

      <!-- Tasks -->
      <div class="executive-card p-5">
        <TaskBoard
          ref="taskBoardRef"
          :project-id="projectId"
          :editable="editable"
          @changed="milestonesRef?.reload()"
        />
      </div>

      <!-- Linked tickets + Upcoming features -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div class="executive-card p-5 flex flex-col gap-3">
          <div class="flex items-center gap-2">
            <div
              class="size-7 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center"
            >
              <LucideTicket class="size-4" />
            </div>
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Linked tickets") }}
            </span>
            <span
              v-if="resource.data.tickets?.length"
              class="text-xs text-ink-gray-5"
            >
              · {{ resource.data.tickets.length }}
            </span>
          </div>
          <div
            v-if="resource.data.tickets?.length"
            class="flex flex-col divide-y divide-outline-gray-1"
          >
            <button
              v-for="t in resource.data.tickets"
              :key="t.name"
              type="button"
              class="group flex items-center gap-3 py-2 px-1 text-start rounded hover:bg-surface-menu-bar"
              @click="openTicket(t.name)"
            >
              <span class="text-sm text-ink-gray-8 truncate flex-1">
                <span class="text-ink-gray-5">#{{ t.name }}</span>
                {{ t.subject }}
              </span>
              <Badge
                :label="t.status"
                :theme="ticketTheme(t.status)"
                variant="subtle"
              />
              <LucideChevronRight
                class="size-3.5 text-ink-gray-4 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              />
            </button>
          </div>
          <p v-else class="text-sm text-ink-gray-5">
            {{ __("No tickets linked to this project yet.") }}
          </p>
        </div>

        <div class="executive-card p-5 flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <div
                class="size-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center"
              >
                <LucideSparkles class="size-4" />
              </div>
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("Upcoming features") }}
              </span>
              <span
                v-if="resource.data.features?.length"
                class="text-xs text-ink-gray-5"
              >
                · {{ resource.data.features.length }}
              </span>
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
  dayjs,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import ProjectComments from "@/components/ProjectComments.vue";
import ProjectMilestones from "@/components/ProjectMilestones.vue";
import TaskBoard from "@/components/TaskBoard.vue";
import LucideTags from "~icons/lucide/tags";
import LucideEyeOff from "~icons/lucide/eye-off";
import LucideTicket from "~icons/lucide/ticket";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideUserRound from "~icons/lucide/user-round";
import LucideUsers from "~icons/lucide/users";
import LucideFlag from "~icons/lucide/flag";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideTrendingUp from "~icons/lucide/trending-up";
import LucideCalendarRange from "~icons/lucide/calendar-range";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideSparkles from "~icons/lucide/sparkles";
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
const PRIORITIES = ["Low", "Medium", "High"];
const editable = computed(() => !isCustomerPortal.value);
const progressPct = computed(
  () => (editable.value ? form.progress : resource.data?.progress) || 0
);
const isInternal = computed(
  () => (resource.data?.project_type || "Customer") === "Internal"
);

const statusAccent = computed(() => {
  const status = editable.value ? form.status : resource.data?.status;
  return (
    {
      Planned: "bg-surface-gray-4",
      Active: "bg-gradient-to-r from-blue-500 to-violet-500",
      "On Hold": "bg-amber-400",
      Completed: "bg-green-500",
      Cancelled: "bg-red-400",
    }[status] || "bg-surface-gray-4"
  );
});

const milestoneStats = computed(() => {
  const rows = resource.data?.milestones || [];
  return {
    total: rows.length,
    done: rows.filter((m: any) => m.status === "Completed").length,
  };
});

const taskStats = computed(() => {
  const rows = resource.data?.tasks || [];
  return {
    total: rows.length,
    done: rows.filter((t: any) => t.status === "Done").length,
  };
});

const timeline = computed(() => {
  const d = resource.data || {};
  const fmt = (v: string) => dayjs(v).format("MMM D");
  const range =
    d.start_date || d.end_date
      ? `${d.start_date ? fmt(d.start_date) : "…"} – ${
          d.end_date ? fmt(d.end_date) : "…"
        }`
      : __("No dates set");
  if (d.status === "Completed")
    return { headline: __("Completed"), range, overdue: false };
  if (!d.end_date) return { headline: __("No target"), range, overdue: false };
  const days = dayjs(d.end_date)
    .startOf("day")
    .diff(dayjs().startOf("day"), "day");
  if (days > 0)
    return { headline: __("{0} days left", [days]), range, overdue: false };
  if (days === 0) return { headline: __("Due today"), range, overdue: false };
  return {
    headline: __("{0} days overdue", [Math.abs(days)]),
    range,
    overdue: true,
  };
});

function priorityChip(priority: string) {
  return (
    {
      Low: "bg-surface-gray-2 text-ink-gray-6",
      Medium: "bg-blue-50 text-blue-700",
      High: "bg-red-50 text-red-700",
    }[priority] || "bg-blue-50 text-blue-700"
  );
}

function ticketTheme(status: string) {
  return (
    {
      Open: "red",
      Replied: "blue",
      Paused: "orange",
      Resolved: "green",
      Closed: "gray",
    }[status] || "gray"
  );
}

const milestonesRef = ref<any>(null);
const taskBoardRef = ref<any>(null);

const form = reactive({
  project_name: "",
  project_type: "Customer",
  customer: "",
  status: "Planned",
  priority: "Medium",
  team: "",
  lead: "",
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
    form.project_type = d.project_type || "Customer";
    form.customer = d.customer || "";
    form.status = d.status || "Planned";
    form.priority = d.priority || "Medium";
    form.team = d.team || "";
    form.lead = d.lead || "";
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
    message: __(
      "This will permanently delete the project with its milestones, tasks and comments."
    ),
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

function newTicket() {
  router.push({
    name: isCustomerPortal.value ? "TicketNew" : "TicketAgentNew",
    query: { project: props.projectId },
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

<style scoped>
.meta-chip {
  @apply inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium;
}
.stat-tile {
  @apply rounded-xl border border-outline-gray-1 bg-surface-gray-1 p-3.5 flex flex-col gap-1.5;
}
</style>
