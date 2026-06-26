<template>
  <div :class="isCustomerPortal && 'bg-customer-portal min-h-full flex flex-col'">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs
          :label="__('Tickets')"
          :route-name="isCustomerPortal ? 'TicketsCustomer' : 'TicketsAgent'"
          :options="dropdownOptions"
          :dropdown-actions="viewActions"
          :current-view="currentView"
        />
      </template>
      <template #right-header>
        <RouterLink
          v-if="!isCustomerPortal"
          class="inline-flex"
          :to="{ name: 'TicketAgentNew' }"
        >
          <Button
            class="rtl:flex-row-reverse"
            :label="__('Create')"
            theme="gray"
            variant="solid"
          >
            <template #prefix>
              <LucidePlus class="h-4 w-4" />
            </template>
          </Button>
        </RouterLink>
      </template>
    </LayoutHeader>
    <div
      v-if="isCustomerPortal"
      class="animate-in-fade px-4 md:px-8 pt-6 pb-4 mt-2 max-w-screen-2xl mx-auto w-full"
    >
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <div
            class="size-12 rounded-2xl hd-icon-blue flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40 shrink-0"
          >
            <LucideTicket class="size-6 text-white" />
          </div>
          <div class="min-w-0">
            <h1
              class="executive-heading text-2xl text-ink-gray-9 leading-tight"
            >
              {{ __("Your tickets") }}
            </h1>
            <p class="text-sm text-ink-gray-6 mt-0.5">
              {{
                __(
                  "Every support request in one place. Use the Create button to open a new one."
                )
              }}
            </p>
          </div>
        </div>
        <RouterLink
          :to="{ name: 'TicketNew' }"
          class="inline-flex shrink-0"
        >
          <Button :label="__('Create')" theme="blue" variant="solid">
            <template #prefix>
              <LucidePlus class="h-4 w-4" />
            </template>
          </Button>
        </RouterLink>
      </div>
      <!-- Portal: stat tiles -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="blue">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-blue flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideTicket class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ portalOpenCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Open") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Awaiting resolution") }}</div>
        </div>
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="amber">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-amber flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideMessageSquare class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ portalRepliedCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Replied") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Awaiting your response") }}</div>
        </div>
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="emerald">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-emerald flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideCircleCheck class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ portalResolvedCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Resolved") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Last 30 days") }}</div>
        </div>
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="violet">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-violet flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideArchive class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ portalTotalCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("All Tickets") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("All time") }}</div>
        </div>
      </div>
    </div>

    <!-- Agent: queue overview dashboard -->
    <div v-if="!isCustomerPortal" class="px-4 md:px-6 pt-4 pb-2">
      <div class="flex items-center gap-2 mb-3 px-0.5">
        <div class="size-1.5 rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
        <span class="text-[11px] font-semibold text-ink-gray-5 uppercase tracking-wider">
          {{ __("Queue Overview") }}
        </span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">

        <!-- Open -->
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="blue">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-blue flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideTicket class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ agentOpenCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Open") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Unresolved") }}</div>
        </div>

        <!-- Unassigned -->
        <div
          class="executive-card flex flex-col gap-2 px-4 pt-5 pb-4"
          :class="agentUnassignedCount ? 'ring-1 ring-amber-200' : ''"
        >
          <div class="flex items-center justify-between gap-2">
            <div
              class="size-8 rounded-xl flex items-center justify-center shadow-md"
              :class="agentUnassignedCount ? 'bg-amber-100' : 'bg-surface-gray-2'"
            >
              <LucideUserX class="size-4" :class="agentUnassignedCount ? 'text-amber-600' : 'text-ink-gray-4'" />
            </div>
            <span class="text-2xl font-bold" :class="agentUnassignedCount ? 'text-amber-700' : 'text-ink-gray-9'">
              {{ agentUnassignedCount }}
            </span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Unassigned") }}</div>
          <div class="text-[11px]" :class="agentUnassignedCount ? 'text-amber-600' : 'text-ink-gray-4'">
            {{ agentUnassignedCount ? __("Need an agent") : __("All assigned") }}
          </div>
        </div>

        <!-- Urgent -->
        <div
          class="executive-card flex flex-col gap-2 px-4 pt-5 pb-4"
          :class="agentUrgentCount ? 'ring-1 ring-red-200' : ''"
        >
          <div class="flex items-center justify-between gap-2">
            <div
              class="size-8 rounded-xl flex items-center justify-center shadow-md"
              :class="agentUrgentCount ? 'bg-red-100' : 'bg-surface-gray-2'"
            >
              <LucideAlertCircle class="size-4" :class="agentUrgentCount ? 'text-red-500' : 'text-ink-gray-4'" />
            </div>
            <span class="text-2xl font-bold" :class="agentUrgentCount ? 'text-red-600' : 'text-ink-gray-9'">
              {{ agentUrgentCount }}
            </span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Urgent") }}</div>
          <div class="text-[11px]" :class="agentUrgentCount ? 'text-red-500' : 'text-ink-gray-4'">
            {{ agentUrgentCount ? __("High priority") : __("None urgent") }}
          </div>
        </div>

        <!-- SLA Failed -->
        <div
          class="executive-card flex flex-col gap-2 px-4 pt-5 pb-4"
          :class="agentSlaFailedCount ? 'ring-1 ring-red-300' : ''"
        >
          <div class="flex items-center justify-between gap-2">
            <div
              class="size-8 rounded-xl flex items-center justify-center shadow-md"
              :class="agentSlaFailedCount ? 'bg-red-100' : 'bg-surface-gray-2'"
            >
              <LucideTimerOff class="size-4" :class="agentSlaFailedCount ? 'text-red-500' : 'text-ink-gray-4'" />
            </div>
            <span class="text-2xl font-bold" :class="agentSlaFailedCount ? 'text-red-600' : 'text-ink-gray-9'">
              {{ agentSlaFailedCount }}
            </span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("SLA Failed") }}</div>
          <div class="text-[11px]" :class="agentSlaFailedCount ? 'text-red-500 font-medium' : 'text-ink-gray-4'">
            {{ agentSlaFailedCount ? __("Breached") : __("All on track") }}
          </div>
        </div>

        <!-- Resolved today -->
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="emerald">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-emerald flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideCircleCheck class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ agentResolvedTodayCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("Resolved Today") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Closed today") }}</div>
        </div>

        <!-- My open -->
        <div class="executive-card hd-color-card flex flex-col gap-2 px-4 pt-5 pb-4" data-accent="violet">
          <div class="flex items-center justify-between gap-2">
            <div class="size-8 rounded-xl hd-icon-violet flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40">
              <LucideUserCheck class="size-4 text-white" />
            </div>
            <span class="text-2xl font-bold text-ink-gray-9">{{ agentMyOpenCount }}</span>
          </div>
          <div class="text-xs font-semibold text-ink-gray-7">{{ __("My Open") }}</div>
          <div class="text-[11px] text-ink-gray-4">{{ __("Assigned to me") }}</div>
        </div>

      </div>
    </div>

    <div
      :class="
        isCustomerPortal
          ? 'flex-1 flex flex-col min-h-0 w-full max-w-screen-2xl mx-auto px-4 md:px-8 pb-6'
          : 'contents'
      "
    >
      <div
        :class="
          isCustomerPortal
            ? 'executive-card hd-colorful-rows flex-1 flex flex-col min-h-0 overflow-hidden bg-surface-white'
            : 'contents hd-colorful-rows'
        "
      >
        <ListViewBuilder
          ref="listViewRef"
          :options="options"
          @row-click="
            (row) =>
              $router.push({
                name: isCustomerPortal ? 'TicketCustomer' : 'TicketAgent',
                params: { ticketId: row },
              })
          "
        />
      </div>
    </div>
    <ExportModal
      v-model="showExportModal"
      :rowCount="$refs.listViewRef?.list?.data?.total_count ?? 0"
      @update="
        ({ export_type, export_all }) => exportRows(export_type, export_all)
      "
    />
    <ViewModal
      v-if="viewDialog.show"
      v-model="viewDialog"
      @update="(view, action) => handleView(view, action)"
    />
    <BulkReplyModal
      v-model="showBulkReplyModal"
      :selections="listSelections"
      @success="listViewRef?.unselectAll()"
    />
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader, ListViewBuilder } from "@/components";
import { EditIcon, PinIcon, TicketIcon, UnpinIcon } from "@/components/icons";
import IndicatorIcon from "@/components/icons/IndicatorIcon.vue";
import BulkReplyModal from "@/components/ticket-agent/BulkReplyModal.vue";
import ExportModal from "@/components/ticket/ExportModal.vue";
import ViewBreadcrumbs from "@/components/ViewBreadcrumbs.vue";
import ViewModal from "@/components/ViewModal.vue";
import { currentView, useView } from "@/composables/useView";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { __ } from "@/translation";
import { View } from "@/types";
import { getIcon, isCustomerPortal, shortDuration } from "@/utils";
import {
  Avatar,
  Badge,
  createResource,
  dayjs,
  FeatherIcon,
  toast,
  Tooltip,
  usePageMeta,
} from "frappe-ui";
import { computed, h, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();

const {
  getCurrentUserViews,
  createView,
  publicViews,
  pinnedViews,
  findView,
  updateView,
  deleteView,
  standardViews,
} = useView("HD Ticket");

const activeView = computed(() => findView(route.query.view as string).value);
const hasActiveFilters = computed(
  () => Object.keys(listViewRef.value?.list?.params?.filters || {}).length > 0
);

const { $dialog, $socket } = globalStore();
const { isManager, userId } = useAuthStore();

// Customer portal: ticket stat chips. Scoped server-side by HD Ticket's
// permission_query (the user's own tickets + their whole customer org's
// tickets) so the chips match the list below. Filtering by raised_by here
// previously showed 0 even when the list had rows raised by other contacts
// of the same customer.
const _portalStatsRes = createResource({
  url: "helpdesk.api.ticket.get_customer_ticket_stats",
  auto: isCustomerPortal.value,
});
const portalOpenCount = computed(() => _portalStatsRes.data?.open ?? 0);
const portalResolvedCount = computed(
  () => _portalStatsRes.data?.resolved_30d ?? 0
);
const portalTotalCount = computed(() => _portalStatsRes.data?.total ?? 0);
const portalRepliedCount = computed(() => _portalStatsRes.data?.replied ?? 0);

// Agent queue stats (agent side only)
const _agentToday = computed(() => new Date().toISOString().split("T")[0]);
const _agentOpenRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { status_category: ["!=", "Resolved"] } }),
  auto: !isCustomerPortal.value,
});
const _agentUnassignedRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { status_category: ["!=", "Resolved"], _assign: ["is", "not set"] } }),
  auto: !isCustomerPortal.value,
});
const _agentUrgentRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { status_category: ["!=", "Resolved"], priority: "Urgent" } }),
  auto: !isCustomerPortal.value,
});
const _agentSlaFailedRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { agreement_status: "Failed", status_category: ["!=", "Resolved"] } }),
  auto: !isCustomerPortal.value,
});
const _agentResolvedTodayRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { status_category: "Resolved", resolution_date: [">=", _agentToday.value] } }),
  auto: !isCustomerPortal.value,
});
const _agentMyOpenRes = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({ doctype: "HD Ticket", filters: { status_category: ["!=", "Resolved"], _assign: ["like", `%${userId}%`] } }),
  auto: !isCustomerPortal.value,
});
const agentOpenCount = computed(() => _agentOpenRes.data ?? 0);
const agentUnassignedCount = computed(() => _agentUnassignedRes.data ?? 0);
const agentUrgentCount = computed(() => _agentUrgentRes.data ?? 0);
const agentSlaFailedCount = computed(() => _agentSlaFailedRes.data ?? 0);
const agentResolvedTodayCount = computed(() => _agentResolvedTodayRes.data ?? 0);
const agentMyOpenCount = computed(() => _agentMyOpenRes.data ?? 0);

const listViewRef = ref(null);
const showExportModal = ref(false);

const { getStatus } = useTicketStatusStore();

// Status renders as a calm subtle Badge in the status's configured color.
// Strong/loud treatment is reserved for genuine alarms (Failed SLA, Urgent).
const STATUS_THEME: Record<string, string> = {
  red: "red",
  green: "green",
  blue: "blue",
  yellow: "orange",
  orange: "orange",
  amber: "orange",
  pink: "red",
  teal: "green",
  cyan: "blue",
  violet: "blue",
  purple: "blue",
  gray: "gray",
  black: "gray",
};

// Only Urgent earns the loud gradient pill; the rest stay subtle.
const URGENT_PILL_CLASS =
  "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold shadow-sm ring-1 ring-inset ring-black/5 bg-gradient-to-r from-red-500 to-rose-500 text-white";

const PRIORITY_THEME: Record<string, string> = {
  High: "orange",
  Medium: "blue",
  Low: "gray",
};

const listSelections = ref(new Set());

const showBulkReplyModal = ref(false);

const selectBannerActions = [
  {
    label: __("Bulk Reply"),
    icon: "lucide-corner-up-left",
    onClick: (selections: Set<string>) => {
      listSelections.value = new Set(selections);
      showBulkReplyModal.value = true;
    },
  },
  {
    label: __("Export"),
    icon: "lucide-download",
    onClick: (selections: Set<string>) => {
      listSelections.value = new Set(selections);
      showExportModal.value = true;
    },
  },
];

const options = computed(() => ({
  doctype: "HD Ticket",
  columnConfig: {
    subject: {
      custom: ({ row, item }) => {
        const seenBy = row._seen ? JSON.parse(row._seen) : [];
        const isSeen = seenBy.includes(userId || "");
        return h(
          "span",
          {
            class: ["truncate flex-1", !isSeen && "font-semibold"],
          },
          item
        );
      },
    },
    status: {
      custom: ({ item }) => {
        const status = getStatus(item);
        let label =
          (isCustomerPortal.value
            ? status?.["label_customer"]
            : status?.["label_agent"]) ||
          item ||
          "";
        // Normalize user-created lowercase status labels (e.g. "reopened")
        label = label.charAt(0).toUpperCase() + label.slice(1);
        const colorKey = (status?.color || "gray").toLowerCase();
        return h(Badge, {
          label,
          theme: STATUS_THEME[colorKey] || "gray",
          variant: "subtle",
        });
      },
    },
    priority: {
      custom: ({ item }) => {
        if (!item) return h("span", { class: "text-ink-gray-4 text-sm" }, "—");
        if (item === "Urgent") {
          return h("span", { class: URGENT_PILL_CLASS }, item);
        }
        return h(Badge, {
          label: item,
          theme: PRIORITY_THEME[item] || "gray",
          variant: "subtle",
        });
      },
    },
    name: {
      custom: ({ item }) => {
        return h(
          "span",
          {
            class:
              "inline-flex items-center font-mono text-xs font-semibold text-blue-700 px-2 py-1 rounded-md bg-blue-50 ring-1 ring-inset ring-blue-200",
          },
          `#${item}`
        );
      },
    },
    _assign: {
      custom: ({ item }) => {
        if (!item) {
          return h(
            "span",
            { class: "text-ink-gray-4 text-sm" },
            __("Unassigned")
          );
        }
        try {
          const users = JSON.parse(item);
          if (!Array.isArray(users) || !users.length) {
            return h(
              "span",
              { class: "text-ink-gray-4 text-sm" },
              __("Unassigned")
            );
          }
          return h(
            "div",
            { class: "flex items-center gap-2 min-w-0" },
            [
              h(Avatar, { label: users[0], size: "sm" }),
              h(
                "span",
                { class: "truncate text-base text-ink-gray-8" },
                users.length > 1
                  ? `${users[0]} +${users.length - 1}`
                  : users[0]
              ),
            ]
          );
        } catch (_) {
          return h("span", { class: "text-ink-gray-4 text-sm" }, "—");
        }
      },
    },
    modified: {
      custom: ({ item }) => {
        if (!item) return h("span", { class: "text-ink-gray-4 text-sm" }, "—");
        return h(
          "span",
          { class: "text-base text-ink-gray-7" },
          dayjs(item).fromNow()
        );
      },
    },
    agreement_status: {
      custom: ({ item }) => {
        return h(Badge, {
          label: __(item),
          theme: slaStatusColorMap[item],
          variant: "subtle",
        });
      },
    },
    response_by: {
      custom: ({ row, item }) => handleResponseByField(row, item),
    },
    resolution_by: {
      custom: ({ row, item }) => handleResolutionByField(row, item),
    },
  },
  isCustomerPortal: isCustomerPortal.value,
  selectable: true,
  showSelectBanner: true,
  selectBannerActions,
  emptyState: {
    title: __("No tickets found"),
    icon: h(TicketIcon, {
      class: "h-10 w-10",
    }),
    description:
      activeView.value?.public || activeView.value?.pinned
        ? __(
            "No tickets found for this view. Try adjusting your filters or creating a new view."
          )
        : hasActiveFilters.value
        ? __(
            "No tickets found for the applied filters. Try adjusting or clearing your filters."
          )
        : undefined,
  },
  rowRoute: {
    name: isCustomerPortal.value ? "TicketCustomer" : "TicketAgent",
    prop: "ticketId",
  },
  hideColumnSetting: false,
}));

function handleResponseByField(row: any, item: string) {
  if (!row.first_responded_on && dayjs(item).isBefore(new Date())) {
    return h(Badge, {
      label: __("Failed"),
      theme: "red",
      variant: "subtle",
    });
  }
  if (row.first_responded_on && dayjs(row.first_responded_on).isBefore(item)) {
    return h(Badge, {
      label: __("Fulfilled"),
      theme: "green",
      variant: "subtle",
    });
  } else if (dayjs(row.first_responded_on).isAfter(item)) {
    return h(Badge, {
      label: __("Failed"),
      theme: "red",
      variant: "subtle",
    });
  } else {
    return h(
      Tooltip,
      {
        text: dayjs(item).format("LLLL"),
      },
      h(Badge, {
        label: shortDuration(item),
        variant: "subtle",
        theme: "orange",
      })
    );
  }
}

function handleResolutionByField(row: any, item: string) {
  const status = getStatus(row.status) || {};
  if (status.category === "Paused") {
    return h(Badge, {
      label: __("Paused"),
      theme: "blue",
      variant: "subtle",
    });
  }
  // Trust the server-computed SLA status for terminal states.
  if (row.agreement_status === "Fulfilled") {
    return h(Badge, {
      label: __("Fulfilled"),
      theme: "green",
      variant: "subtle",
    });
  }
  if (row.agreement_status === "Failed") {
    return h(Badge, {
      label: __("Failed"),
      theme: "red",
      variant: "subtle",
    });
  }
  // In progress without a resolution deadline to track.
  if (!item) {
    return h(Badge, {
      label: __("—"),
      theme: "gray",
      variant: "subtle",
    });
  }
  // In progress but the resolution deadline has already passed.
  if (dayjs(item).isBefore(dayjs())) {
    return h(Badge, {
      label: __("Failed"),
      theme: "red",
      variant: "subtle",
    });
  }
  // In progress with a future deadline: show the live countdown.
  return h(
    Tooltip,
    {
      text: dayjs(item).format("LLLL"),
    },
    h(Badge, {
      label: shortDuration(item),
      variant: "subtle",
      theme: "orange",
    })
  );
}

async function exportRows(
  export_type: "CSV" | "Excel" = "Excel",
  export_all: boolean = false
) {
  const list = listViewRef.value?.list;
  if (!list) return;

  const fields = JSON.stringify(list.data.columns.map((f) => f.key));
  const order_by = list.params.order_by;

  let filters = { ...list.params.filters };
  // Resolve `@me` filters to the current session user before export
  Object.keys(filters).forEach((key) => {
    const value = filters[key];

    // Handle direct filter format: { owner: "@me" }
    if (value === "@me") {
      filters[key] = userId;
      return;
    }
    if (!Array.isArray(value)) return;

    // Handle all operator-based filter format: { owner: ["=", "@me"], _assign: ["LIKE", "%@me%"] }
    filters[key] = value.map((entry) =>
      entry === "@me" ? userId : entry === "%@me%" ? `%${userId}%` : entry
    );
  });
  let pageLength: number;

  if (export_all) {
    filters = JSON.stringify(filters);
    pageLength = list.data.total_count;
  } else {
    pageLength = listSelections.value.size;
    filters["name"] = ["in", Array.from(listSelections.value)];
    filters = JSON.stringify(filters);
  }

  window.location.href = `/api/method/frappe.desk.reportview.export_query?file_format_type=${export_type}&title=HD Ticket&doctype=HD Ticket&fields=${fields}&filters=${encodeURIComponent(
    filters
  )}&order_by=${order_by}&page_length=${pageLength}&start=0&view=Report&with_comment_count=1`;
  reset();
  showExportModal.value = false;
}

function reset(reload = false) {
  listViewRef.value?.unselectAll();
  listSelections.value?.clear();
  if (reload) listViewRef.value.reload();
}

const slaStatusColorMap = {
  Fulfilled: "green",
  Failed: "red",
  "Resolution Due": "orange",
  "First Response Due": "orange",
  Paused: "blue",
};

let viewDialog = reactive({
  show: false,
  view: {
    label: "",
    icon: "",
    name: "",
  },
  mode: "create",
});

const dropdownOptions = computed(() => {
  const items = [
    {
      group: __("Default Views"),
      items: [
        {
          label: __("List View"),
          icon: "lucide-align-justify",
          onClick: () =>
            router.push({
              name: isCustomerPortal.value ? "TicketsCustomer" : "TicketsAgent",
            }),
        },
      ],
    },
  ];

  // Saved Views
  if (getCurrentUserViews.value?.length !== 0) {
    items.push({
      group: __("Saved Views"),
      items: parseViews(getCurrentUserViews.value),
    });
  }
  if (pinnedViews.value?.length !== 0) {
    items.push({
      group: __("Private Views"),
      items: parseViews(pinnedViews.value),
    });
  }

  const allPublicViews = [
    ...(standardViews.value || []),
    ...(publicViews.value || []),
  ];

  const uniquePublicViews = Array.from(
    new Map(allPublicViews.map((v) => [v.name, v])).values()
  );

  items.push({
    group: __("Public Views"),
    items: parseViews(uniquePublicViews),
  });

  items.push({
    group: __("Create View"),
    hideLabel: true,
    items: [
      {
        label: __("Create View"),
        icon: "lucide-plus",
        onClick: () => {
          resetState();
          viewDialog.show = true;
        },
      },
    ],
  });

  return items;
});

let selectedView: View | null = null;

const toggleViewVisibility = (_view: any, title: string, message: string) => {
  const newView: any = {
    name: _view.name,
    public: !_view.public,
  };

  if (_view.public) {
    $dialog({
      title,
      message,
      actions: [
        {
          label: __("Confirm"),
          variant: "solid",
          onClick({ close }: any) {
            close();
            updateView(newView);
          },
        },
      ],
    });
  } else {
    updateView(newView);
  }
};

const viewActions = (view) => {
  const _view = findView(view.name).value;

  let actions = [
    {
      group: __("Default Views"),
      hideLabel: true,
      items: [
        {
          label: __("Duplicate"),
          icon: h(FeatherIcon, { name: "copy" }),
          onClick: () => {
            viewDialog.view.label = _view.label + " (New)";
            viewDialog.view.icon = _view.icon;
            viewDialog.view.name = _view.name;
            viewDialog.mode = "duplicate";
            selectedView = _view;
            viewDialog.show = true;
          },
        },
      ],
    },
  ];
  if (!_view.public || isManager) {
    if (!_view.public && !_view.is_standard) {
      actions[0].items.push({
        label: _view?.pinned ? __("Unpin View") : __("Pin View"),
        icon: h(_view?.pinned ? UnpinIcon : PinIcon, { class: "h-4 w-4" }),
        onClick: () => {
          const newView = {
            name: _view.name,
          };
          newView["pinned"] = !_view.pinned;
          updateView(newView);
        },
      });
    }
    if (_view?.is_standard && isManager) {
      actions[0].items.push({
        label: _view?.public ? __("Hide from sidebar") : __("Show in sidebar"),
        icon: h(FeatherIcon, {
          name: _view?.public ? "eye-off" : "eye",
          class: "h-4 w-4",
        }),
        onClick: () => {
          toggleViewVisibility(
            _view,
            __("Hide view from sidebar"),
            __(
              "{0} view is currently visible in the sidebar. Hiding it will remove it from the sidebar.",
              [_view.label]
            )
          );
        },
      });
    }
    if (!_view.is_standard) {
      if (isManager && !isCustomerPortal.value) {
        actions[0].items.push({
          label: _view?.public ? __("Make Private") : __("Make Public"),
          icon: h(FeatherIcon, {
            name: _view?.public ? "lock" : "unlock",
            class: "h-4 w-4",
          }),
          onClick: () => {
            toggleViewVisibility(
              _view,
              __("Make view private"),
              __(
                "{0} view is currently public. Changing it to private will hide it for all the users.",
                [_view.label]
              )
            );
          },
        });
      }
      actions[0].items.push({
        label: __("Edit"),
        icon: h(EditIcon, { class: "h-4 w-4" }),
        onClick: () => {
          viewDialog.view.label = _view.label;
          viewDialog.view.icon = _view.icon;
          viewDialog.view.name = _view.name;
          viewDialog.mode = "edit";
          viewDialog.show = true;
        },
      });
      actions.push({
        group: __("Delete View"),
        hideLabel: true,
        items: [
          {
            label: __("Delete"),
            icon: "lucide-trash-2",
            theme: "red",
            onClick: () => {
              $dialog({
                title: __("Delete {0}", [_view.label]),
                message:
                  __("Are you sure you want to delete this view?") +
                  (_view.public
                    ? " " +
                      __(
                        "This view is public, and will be removed for all users."
                      )
                    : ""),
                actions: [
                  {
                    label: __("Confirm"),
                    variant: "solid",
                    iconLeft: "trash-2",
                    theme: "red",
                    onClick({ close }) {
                      if (route.query.view === _view.name) {
                        router.push({
                          name: isCustomerPortal.value
                            ? "TicketsCustomer"
                            : "TicketsAgent",
                        });
                      }
                      deleteView(_view.name);
                      handleSuccess(__("deleted"));
                      close();
                    },
                  },
                ],
              });
            },
          },
        ],
      });
    }
  }
  return actions;
};

function parseViews(views: View[]) {
  return views?.map((view) => {
    return {
      ...view,
      onClick: () => {
        currentView.value = {
          label: view.label,
          icon: view.icon,
        };
        router.push({
          name: view.route_name,
          query: {
            view: view.name,
          },
        });
      },
    };
  });
}

function handleView(viewInfo, action) {
  let view: View;
  if (action === "update") {
    updateView(viewInfo);
    handleSuccess("updated");
    currentView.value = {
      label: viewInfo.label,
      icon: getIcon(viewInfo.icon),
    };
    return;
  } else if (action === "duplicate") {
    view = {
      ...selectedView,
      filters: JSON.stringify(selectedView.filters),
      columns: JSON.stringify(selectedView.columns),
      rows: JSON.stringify(selectedView.rows),
      label: viewInfo.label,
      icon: viewInfo.icon,
      public: false,
      pinned: false,
    };
  } else {
    view = {
      dt: "HD Ticket",
      type: "list",
      label: viewInfo.label ?? __("List"),
      icon: viewInfo.icon ?? "",
      route_name: router.currentRoute.value.name as string,
      order_by: listViewRef.value?.list?.params.order_by,
      filters: JSON.stringify(listViewRef.value?.list?.params.filters),
      columns: JSON.stringify(listViewRef.value?.list?.data.columns),
      rows: JSON.stringify(listViewRef.value?.list?.data?.rows),
      is_customer_portal: isCustomerPortal.value,
    };
  }

  // createView
  createView(view, (d) => {
    currentView.value = {
      label: d.label || __("List"),
      icon: getIcon(d.icon),
    };
    router.push({
      name: isCustomerPortal.value ? "TicketsCustomer" : "TicketsAgent",
      query: {
        view: d.name,
      },
    });

    handleSuccess();
  });
}

function handleSuccess(msg = __("created")) {
  toast.success(__("View {0}", [msg]));
  resetState();
}
function resetState() {
  viewDialog.show = false;
  viewDialog.view.label = "";
  viewDialog.view.icon = "";
  viewDialog.view.name = "";
  viewDialog.mode = null;
  selectedView = null;
}

onMounted(() => {
  if (!route.query.view) {
    currentView.value = {
      label: __("List"),
      icon: LucideAlignJustify,
    };
  }
  if (!isCustomerPortal.value) {
    $socket.on("helpdesk:new-ticket", () => {
      listViewRef.value?.reload();
    });
  }
});

onUnmounted(() => {
  if (!isCustomerPortal.value) {
    $socket.off("helpdesk:new-ticket");
  }
});

usePageMeta(() => {
  return {
    title: __("Tickets"),
  };
});
</script>
