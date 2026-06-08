<template>
  <div class="overflow-y-auto h-full bg-customer-portal flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideBuilding2 class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Company tickets") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <Button
          variant="subtle"
          theme="blue"
          @click="router.push({ name: 'TicketNew' })"
        >
          <template #prefix><LucidePlus class="size-4" /></template>
          <span class="hidden md:inline">{{ __("New ticket") }}</span>
        </Button>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-5 flex-1"
    >
      <!-- No company linked -->
      <div
        v-if="!companies.loading && !companyNames.length"
        class="executive-card flex flex-col items-center justify-center text-center py-14 gap-2"
      >
        <div
          class="size-12 rounded-full bg-surface-gray-2 flex items-center justify-center"
        >
          <LucideBuilding2 class="size-6 text-ink-gray-5" />
        </div>
        <p class="font-medium text-ink-gray-8">
          {{ __("You're not linked to a company yet") }}
        </p>
        <p class="text-sm text-ink-gray-5 max-w-sm">
          {{
            __(
              "Once your account is associated with an organization, your colleagues' tickets will appear here."
            )
          }}
        </p>
      </div>

      <template v-else>
        <!-- Hero -->
        <section
          class="hd-brand-hero rounded-2xl px-6 py-5 md:px-8 flex flex-col md:flex-row md:items-center justify-between gap-3 animate-in-fade"
        >
          <div>
            <div class="executive-heading text-2xl text-white leading-tight">
              {{ companyLabel }}
            </div>
            <div class="text-sm hd-on-navy-soft mt-1">
              {{ __("All tickets from your organization") }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-for="opt in scopeOptions"
              :key="opt.value"
              type="button"
              class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border"
              :class="
                scope === opt.value
                  ? 'bg-white/15 border-white/30 text-white'
                  : 'border-white/15 text-white/70 hover:text-white'
              "
              @click="scope = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </section>

        <!-- List -->
        <div class="executive-card divide-y divide-outline-gray-1">
          <div
            v-if="tickets.loading && !tickets.data?.length"
            class="p-4 flex flex-col gap-2"
          >
            <div
              v-for="i in 5"
              :key="i"
              class="h-12 rounded bg-surface-gray-2 animate-pulse"
            />
          </div>

          <button
            v-for="t in tickets.data"
            :key="t.name"
            type="button"
            class="w-full text-start px-4 py-3 flex items-center gap-3 hover:bg-surface-menu-bar transition-colors"
            @click="open(t.name)"
          >
            <Avatar size="md" :label="t.raised_by" />
            <div class="min-w-0 flex-1">
              <div class="text-sm font-medium text-ink-gray-8 truncate">
                #{{ t.name }} · {{ t.subject || __("(no subject)") }}
              </div>
              <div class="text-xs text-ink-gray-5 truncate">
                {{ t.raised_by }} · {{ timeAgo(t.modified) }}
              </div>
            </div>
            <span
              v-if="t.priority"
              class="hidden sm:inline text-xs text-ink-gray-6 shrink-0"
            >
              {{ t.priority }}
            </span>
            <Badge
              v-if="t.status"
              :label="customerStatus(t.status)"
              :theme="statusTheme(t.status)"
              variant="subtle"
            />
          </button>

          <div
            v-if="!tickets.loading && !tickets.data?.length"
            class="px-4 py-12 text-center text-sm text-ink-gray-5"
          >
            {{ __("No tickets to show for this view.") }}
          </div>
        </div>
      </template>
    </div>
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
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import { useConfigStore } from "@/stores/config";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { timeAgo } from "@/utils";
import { __ } from "@/translation";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucidePlus from "~icons/lucide/plus";

const router = useRouter();
const config = useConfigStore();
const { getStatus } = useTicketStatusStore();

const companies = createResource({
  url: "helpdesk.api.contact.get_my_companies",
  auto: true,
});
const companyNames = computed<string[]>(() =>
  (companies.data || []).map((c: any) => c.name)
);
const companyLabel = computed(() =>
  companyNames.value.length === 1
    ? companyNames.value[0]
    : config.brandName || __("Your organization")
);

const scope = ref<"all" | "open">("all");
const scopeOptions = [
  { value: "all" as const, label: __("All") },
  { value: "open" as const, label: __("Open") },
];

const tickets = createListResource({
  doctype: "HD Ticket",
  fields: ["name", "subject", "status", "priority", "raised_by", "modified"],
  filters: computed(() => {
    const f: Record<string, any> = { customer: ["in", companyNames.value] };
    if (scope.value === "open") f.status_category = ["!=", "Resolved"];
    return f;
  }),
  orderBy: "modified desc",
  pageLength: 50,
  auto: false,
});

watch(
  [companyNames, scope],
  () => {
    if (companyNames.value.length) tickets.reload();
  },
  { immediate: true }
);

function customerStatus(status: string) {
  return getStatus(status)?.label_customer || status;
}
function statusTheme(status: string) {
  const cat = getStatus(status)?.category;
  if (cat === "Resolved") return "green";
  if (cat === "Paused") return "orange";
  return "blue";
}
function open(name: string) {
  router.push({ name: "TicketCustomer", params: { ticketId: name } });
}

usePageMeta(() => ({
  title: `${config.brandName || __("Support")} — ${__("Company tickets")}`,
}));
</script>
