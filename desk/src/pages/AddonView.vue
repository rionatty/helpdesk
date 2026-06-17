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
          <ReminderButton
            v-if="resource.data"
            doctype="HD Addon"
            :docname="addonId"
          />
          <Button
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
              theme="gray"
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
      <!-- Header / info -->
      <div class="executive-card p-6 flex flex-col gap-4">
        <div class="flex items-start gap-4">
          <div
            class="size-12 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center shrink-0 shadow-sm"
          >
            <LucidePackage class="size-6 text-white" />
          </div>
          <div class="min-w-0 flex-1">
            <input
              v-if="editable"
              v-model="form.addon_name"
              class="w-full text-2xl font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
            />
            <h1 v-else class="text-2xl font-semibold text-ink-gray-9">
              {{ resource.data.addon_name }}
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

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Version") }}</span>
            <input
              v-if="editable"
              v-model="form.version"
              type="text"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.version || "—" }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Activated on") }}</span>
            <input
              v-if="editable"
              v-model="form.activated_on"
              type="date"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.activated_on || "—" }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Renewal date") }}</span>
            <input
              v-if="editable"
              v-model="form.renewal_date"
              type="date"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
            <span v-else class="text-sm text-ink-gray-8">
              {{ resource.data.renewal_date || "—" }}
            </span>
          </div>
        </div>

        <div class="flex flex-col gap-1">
          <span class="text-xs text-ink-gray-5">{{ __("Notes") }}</span>
          <textarea
            v-if="editable"
            v-model="form.notes"
            rows="2"
            class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
          />
          <p v-else class="text-sm text-ink-gray-8 whitespace-pre-line">
            {{ resource.data.notes || __("No notes.") }}
          </p>
        </div>
      </div>

      <!-- Dashboard -->
      <div class="flex flex-col gap-3">
        <!-- Section label -->
        <div class="flex items-center gap-2 px-0.5">
          <div class="size-1.5 rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
          <span class="text-[11px] font-semibold text-ink-gray-5 uppercase tracking-wider">
            {{ __("Add-on Health Dashboard") }}
          </span>
        </div>

        <!-- Row 1 — Task status -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <!-- Pending -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="amber">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-amber flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideCircleDot class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonTaskBreakdown.todo }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Tasks Pending") }}</div>
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div class="h-full bg-amber-400 rounded-full transition-all duration-700" :style="{ width: addonTaskBreakdown.todoPct + '%' }" />
            </div>
            <div class="text-[11px] text-ink-gray-4">{{ addonTaskBreakdown.todoPct }}% &nbsp;·&nbsp; {{ addonTaskBreakdown.total }} total</div>
          </div>

          <!-- In Progress -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="blue">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-blue flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideLoader2 class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonTaskBreakdown.inprogress }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Tasks In Progress") }}</div>
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div class="h-full bg-blue-500 rounded-full transition-all duration-700" :style="{ width: addonTaskBreakdown.inprogressPct + '%' }" />
            </div>
            <div class="text-[11px] text-ink-gray-4">{{ addonTaskBreakdown.inprogressPct }}% of tasks</div>
          </div>

          <!-- Done -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="emerald">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-emerald flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideCircleCheck class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonTaskBreakdown.done }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Tasks Done") }}</div>
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div class="h-full bg-emerald-500 rounded-full transition-all duration-700" :style="{ width: addonTaskBreakdown.donePct + '%' }" />
            </div>
            <div class="text-[11px] text-ink-gray-4">{{ addonTaskBreakdown.donePct }}% complete</div>
          </div>

          <!-- Blocked -->
          <div
            class="executive-card flex flex-col gap-2 px-4 pt-5 pb-4"
            :class="addonTaskBreakdown.blocked ? 'ring-1 ring-red-200' : ''"
          >
            <div class="flex items-center justify-between gap-2">
              <div
                class="size-8 rounded-xl flex items-center justify-center shadow-md"
                :class="addonTaskBreakdown.blocked ? 'bg-red-100' : 'bg-surface-gray-2'"
              >
                <LucideCircleX class="size-4" :class="addonTaskBreakdown.blocked ? 'text-red-500' : 'text-ink-gray-4'" />
              </div>
              <span class="text-2xl font-bold" :class="addonTaskBreakdown.blocked ? 'text-red-600' : 'text-ink-gray-9'">
                {{ addonTaskBreakdown.blocked }}
              </span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Tasks Blocked") }}</div>
            <div class="text-[11px]" :class="addonTaskBreakdown.blocked ? 'text-red-500' : 'text-ink-gray-4'">
              {{ addonTaskBreakdown.blocked ? addonTaskBreakdown.blocked + " need attention" : "All clear" }}
            </div>
          </div>
        </div>

        <!-- Row 2 — Features + Tickets + Renewal -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <!-- Features in progress -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="violet">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-violet flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideSparkles class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonFeatureBreakdown.inprogress }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Features Active") }}</div>
            <div class="text-[11px] text-ink-gray-4">
              {{ addonFeatureBreakdown.planned }} planned &nbsp;·&nbsp; {{ addonFeatureBreakdown.total }} total
            </div>
            <div v-if="addonFeatureBreakdown.deprecated" class="text-[11px] text-ink-gray-4">
              {{ addonFeatureBreakdown.deprecated }} deprecated
            </div>
          </div>

          <!-- Features released -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="emerald">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-emerald flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideRocket class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonFeatureBreakdown.released }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Features Released") }}</div>
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div
                class="h-full bg-emerald-500 rounded-full transition-all duration-700"
                :style="{ width: addonFeatureBreakdown.total ? Math.round(addonFeatureBreakdown.released / addonFeatureBreakdown.total * 100) + '%' : '0%' }"
              />
            </div>
            <div class="text-[11px] text-ink-gray-4">{{ addonFeatureBreakdown.released }} / {{ addonFeatureBreakdown.total }}</div>
          </div>

          <!-- Open tickets -->
          <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="blue">
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl hd-icon-blue flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
                <LucideTicket class="size-4 text-white" />
              </div>
              <span class="text-2xl font-bold text-ink-gray-9">{{ addonOpenTickets }}</span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Open Tickets") }}</div>
            <div class="text-[11px] text-ink-gray-4">{{ dash.tickets_total }} {{ __("total linked") }}</div>
          </div>

          <!-- Renewal countdown -->
          <div
            class="executive-card flex flex-col gap-2 px-4 pt-5 pb-4"
            :class="renewalInfo.textClass === 'text-red-500' ? 'ring-1 ring-red-200' : ''"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="size-8 rounded-xl flex items-center justify-center shadow-md" :class="renewalInfo.bgClass">
                <LucideCalendarClock class="size-4" :class="renewalInfo.iconColor" />
              </div>
              <span class="text-lg font-bold leading-tight text-right" :class="renewalInfo.textClass">
                {{ renewalInfo.label }}
              </span>
            </div>
            <div class="text-xs font-semibold text-ink-gray-7">{{ __("Renewal") }}</div>
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div class="h-full rounded-full transition-all duration-700" :class="renewalInfo.barClass" :style="{ width: renewalInfo.barPct + '%' }" />
            </div>
            <div class="text-[11px]" :class="renewalInfo.textClass">{{ renewalInfo.sub }}</div>
          </div>
        </div>
      </div>

      <!-- Features -->
      <div class="executive-card p-5">
        <AddonFeatures
          :addon-id="addonId"
          :editable="editable"
          @changed="resource.reload()"
        />
      </div>

      <!-- Tasks -->
      <div class="executive-card p-5">
        <TaskBoard
          :addon-id="addonId"
          :editable="editable"
          @changed="resource.reload()"
        />
      </div>

      <!-- Assigned Agents -->
      <div v-if="editable || members.length" class="executive-card p-5 flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <div
            class="size-7 rounded-lg bg-violet-100 text-violet-700 flex items-center justify-center"
          >
            <LucideUsers class="size-4" />
          </div>
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Assigned Agents") }}
          </span>
          <span v-if="members.length" class="text-xs text-ink-gray-5">
            · {{ members.length }}
          </span>
        </div>

        <div class="flex flex-wrap gap-2">
          <div
            v-for="m in members"
            :key="m.name"
            class="flex items-center gap-1.5 rounded-full px-2.5 py-1 bg-surface-gray-1 border border-outline-gray-1 text-sm text-ink-gray-8"
          >
            <Avatar size="xs" :label="m.agent_name" />
            <span>{{ m.agent_name }}</span>
            <button
              v-if="editable"
              class="text-ink-gray-4 hover:text-red-500 transition-colors"
              @click="removeMember(m.name)"
            >
              <LucideX class="size-3" />
            </button>
          </div>
          <p v-if="!members.length" class="text-sm text-ink-gray-4">
            {{ __("No agents assigned yet.") }}
          </p>
        </div>

        <div v-if="editable" class="max-w-xs">
          <Link doctype="HD Agent" v-model="addAgentVal" :hide-me="true" />
        </div>
      </div>

      <!-- Attachments -->
      <div class="executive-card p-5">
        <DocAttachments
          doctype="HD Addon"
          :docname="addonId"
          :editable="editable"
        />
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
          {{ __("No tickets linked to this add-on yet.") }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  Avatar,
  Badge,
  Breadcrumbs,
  Button,
  call,
  createResource,
  dayjs,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import AddonFeatures from "@/components/AddonFeatures.vue";
import DocAttachments from "@/components/DocAttachments.vue";
import ReminderButton from "@/components/ReminderButton.vue";
import TaskBoard from "@/components/TaskBoard.vue";
import { globalStore } from "@/stores/globalStore";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import LucidePackage from "~icons/lucide/package";
import LucideTicket from "~icons/lucide/ticket";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideClipboardList from "~icons/lucide/clipboard-list";
import LucideUsers from "~icons/lucide/users";
import LucideX from "~icons/lucide/x";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideLoader2 from "~icons/lucide/loader-2";
import LucideCircleCheck from "~icons/lucide/circle-check";
import LucideCircleX from "~icons/lucide/circle-x";
import LucideSparkles from "~icons/lucide/sparkles";
import LucideRocket from "~icons/lucide/rocket";
import LucideCalendarClock from "~icons/lucide/calendar-clock";
import LucideActivity from "~icons/lucide/activity";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideFlag from "~icons/lucide/flag";

interface P {
  addonId: string;
}
const props = defineProps<P>();
const router = useRouter();
const { $dialog } = globalStore();

const STATUSES = ["Active", "Trial", "Suspended", "Retired"];
const editable = computed(() => !isCustomerPortal.value);

// --- Assigned agents ---
const members = ref<any[]>([]);
const addAgentVal = ref<string | null>(null);

const membersRes = createResource({
  url: "helpdesk.api.addon.get_addon_members",
  makeParams: () => ({ addon: props.addonId }),
  auto: editable.value,
  onSuccess: (data: any) => { members.value = data || []; },
});

watch(addAgentVal, async (val) => {
  if (!val) return;
  try {
    await call("helpdesk.api.addon.add_addon_member", {
      addon: props.addonId,
      agent: val,
    });
    membersRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not add agent"));
  }
  addAgentVal.value = null;
});

async function removeMember(name: string) {
  try {
    await call("helpdesk.api.addon.remove_addon_member", { name });
    membersRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not remove agent"));
  }
}

const form = reactive({
  addon_name: "",
  status: "Active",
  version: "",
  activated_on: "",
  renewal_date: "",
  notes: "",
});

const resource = createResource({
  url: "helpdesk.api.addon.get_addon",
  makeParams: () => ({ name: props.addonId }),
  auto: true,
  onSuccess: (d: any) => {
    form.addon_name = d.addon_name || "";
    form.status = d.status || "Active";
    form.version = d.version || "";
    form.activated_on = d.activated_on || "";
    form.renewal_date = d.renewal_date || "";
    form.notes = d.notes || "";
  },
  onError: (e: any) => {
    toast.error(e?.messages?.[0] || e?.message || __("Could not load add-on"));
    router.replace({ name: isCustomerPortal.value ? "AddonsCustomer" : "AddonsAgent" });
  },
});

const dash = computed(
  () =>
    resource.data?.dashboard || {
      features_total: 0,
      features_by_status: {},
      tasks_total: 0,
      tasks_by_status: {},
      tickets_total: 0,
    }
);

const addonTaskBreakdown = computed(() => {
  const s = dash.value.tasks_by_status || {};
  const total = Math.max(dash.value.tasks_total || 0, 1);
  const todo = s["To Do"] || 0;
  const inprogress = s["In Progress"] || 0;
  const done = s["Done"] || 0;
  const blocked = s["Blocked"] || 0;
  return {
    todo, inprogress, done, blocked,
    total: dash.value.tasks_total || 0,
    todoPct: Math.round((todo / total) * 100),
    inprogressPct: Math.round((inprogress / total) * 100),
    donePct: Math.round((done / total) * 100),
  };
});

const addonFeatureBreakdown = computed(() => {
  const s = dash.value.features_by_status || {};
  return {
    planned: s["Planned"] || 0,
    inprogress: s["In Progress"] || 0,
    released: s["Released"] || 0,
    deprecated: s["Deprecated"] || 0,
    total: dash.value.features_total || 0,
  };
});

const addonOpenTickets = computed(
  () =>
    (resource.data?.tickets || []).filter(
      (t: any) => t.status !== "Resolved" && t.status !== "Closed"
    ).length
);

const renewalInfo = computed(() => {
  const rd = resource.data?.renewal_date;
  if (!rd)
    return { label: "Not set", sub: "No renewal date", bgClass: "bg-surface-gray-2", iconColor: "text-ink-gray-4", textClass: "text-ink-gray-5", barClass: "bg-surface-gray-3", barPct: 0 };
  const days = dayjs(rd).startOf("day").diff(dayjs().startOf("day"), "day");
  if (days < 0)
    return { label: Math.abs(days) + "d overdue", sub: "Renewal past due!", bgClass: "bg-red-100", iconColor: "text-red-500", textClass: "text-red-500", barClass: "bg-red-500", barPct: 100 };
  if (days === 0)
    return { label: "Due today", sub: "Action required", bgClass: "bg-red-100", iconColor: "text-red-500", textClass: "text-red-500", barClass: "bg-red-400", barPct: 100 };
  if (days <= 30)
    return { label: days + " days", sub: "Until renewal", bgClass: "bg-amber-100", iconColor: "text-amber-600", textClass: "text-amber-600", barClass: "bg-amber-400", barPct: Math.round((1 - days / 30) * 100) };
  if (days <= 90)
    return { label: days + " days", sub: "Until renewal", bgClass: "bg-blue-100", iconColor: "text-blue-600", textClass: "text-blue-600", barClass: "bg-blue-500", barPct: Math.round((1 - days / 90) * 100) };
  return { label: days + " days", sub: "Until renewal", bgClass: "bg-emerald-100", iconColor: "text-emerald-600", textClass: "text-emerald-600", barClass: "bg-emerald-500", barPct: 0 };
});

const breadcrumbs = computed(() => [
  {
    label: __("Add-ons"),
    route: { name: isCustomerPortal.value ? "AddonsCustomer" : "AddonsAgent" },
  },
  { label: resource.data?.addon_name || props.addonId },
]);

function statusTheme(status: string) {
  return (
    { Active: "green", Trial: "blue", Suspended: "orange", Retired: "gray" }[
      status
    ] || "gray"
  );
}

const saveRes = createResource({
  url: "helpdesk.api.addon.update_addon",
  onSuccess: () => {
    toast.success(__("Saved"));
    resource.reload();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not save")),
});
function save() {
  saveRes.submit({ name: props.addonId, ...form });
}

const deleteRes = createResource({
  url: "helpdesk.api.addon.delete_addon",
  onSuccess: () => {
    toast.success(__("Add-on deleted"));
    router.replace({ name: "AddonsAgent" });
  },
});
function confirmDelete() {
  $dialog({
    title: __("Delete add-on"),
    message: __("This deletes the add-on and its features and tasks."),
    actions: [
      {
        label: __("Delete"),
        theme: "red",
        variant: "solid",
        onClick: (close: Function) => {
          deleteRes.submit({ name: props.addonId });
          close();
        },
      },
    ],
  });
}

function newTicket() {
  router.push({
    name: isCustomerPortal.value ? "TicketNew" : "TicketAgentNew",
    query: { addon: props.addonId },
  });
}
function openTicket(name: string) {
  router.push({
    name: isCustomerPortal.value ? "TicketCustomer" : "TicketAgent",
    params: { ticketId: name },
  });
}

usePageMeta(() => ({ title: resource.data?.addon_name || __("Add-on") }));
</script>
