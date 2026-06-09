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
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="executive-card hd-color-card p-5 pt-6" data-accent="blue">
          <div class="flex items-center gap-2 mb-2">
            <LucideListChecks class="size-4 text-blue-600" />
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Features") }}
            </span>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9">
            {{ dash.features_total }}
          </div>
          <div class="flex flex-wrap gap-1.5 mt-2">
            <span
              v-for="(n, s) in dash.features_by_status"
              :key="s"
              class="text-[11px] rounded-full px-2 py-0.5 bg-surface-gray-2 text-ink-gray-7"
            >
              {{ s }}: {{ n }}
            </span>
          </div>
        </div>

        <div
          v-if="!isCustomerPortal"
          class="executive-card hd-color-card p-5 pt-6"
          data-accent="violet"
        >
          <div class="flex items-center gap-2 mb-2">
            <LucideClipboardList class="size-4 text-violet-600" />
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Tasks") }}
            </span>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9">
            {{ dash.tasks_total }}
          </div>
          <div class="flex flex-wrap gap-1.5 mt-2">
            <span
              v-for="(n, s) in dash.tasks_by_status"
              :key="s"
              class="text-[11px] rounded-full px-2 py-0.5 bg-surface-gray-2 text-ink-gray-7"
            >
              {{ s }}: {{ n }}
            </span>
          </div>
        </div>

        <div class="executive-card hd-color-card p-5 pt-6" data-accent="emerald">
          <div class="flex items-center gap-2 mb-2">
            <LucideTicket class="size-4 text-emerald-600" />
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Tickets") }}
            </span>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9">
            {{ dash.tickets_total }}
          </div>
          <div class="text-xs text-ink-gray-5 mt-2">
            {{ __("Linked to this add-on") }}
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

      <!-- Tasks (agent only) -->
      <div v-if="!isCustomerPortal" class="executive-card p-5">
        <AddonTasks :addon-id="addonId" @changed="resource.reload()" />
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
import { computed, reactive } from "vue";
import {
  Badge,
  Breadcrumbs,
  Button,
  createResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import AddonFeatures from "@/components/AddonFeatures.vue";
import AddonTasks from "@/components/AddonTasks.vue";
import { globalStore } from "@/stores/globalStore";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import LucidePackage from "~icons/lucide/package";
import LucideTicket from "~icons/lucide/ticket";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideClipboardList from "~icons/lucide/clipboard-list";

interface P {
  addonId: string;
}
const props = defineProps<P>();
const router = useRouter();
const { $dialog } = globalStore();

const STATUSES = ["Active", "Trial", "Suspended", "Retired"];
const editable = computed(() => !isCustomerPortal.value);

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
