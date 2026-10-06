<template>
  <div class="flex h-full flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideFileText class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">{{ __("Job cards") }}</div>
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <Button
            v-if="isManager"
            variant="ghost"
            :label="__('Print settings')"
            @click="openSettings"
          />
          <Button variant="solid" :label="__('New job card')" @click="openCard(null)">
            <template #prefix><LucidePlus class="size-4" /></template>
          </Button>
        </div>
      </template>
    </LayoutHeader>

    <div
      class="mx-auto flex w-full max-w-screen-2xl flex-1 flex-col gap-4 overflow-y-auto px-4 py-6 md:px-6 lg:px-8"
    >
      <div class="flex flex-wrap items-center gap-3">
        <FormControl
          v-model="search"
          class="w-full sm:w-72"
          :placeholder="__('Search number, client, ticket or contact')"
          :aria-label="__('Search job cards')"
        />
        <FormControl
          v-model="status"
          class="w-44"
          type="select"
          :options="STATUS_OPTIONS"
          :aria-label="__('Status')"
        />
      </div>

      <div
        v-if="cards.loading && !cards.data"
        class="py-16 text-center text-sm text-ink-gray-5"
      >
        {{ __("Loading...") }}
      </div>
      <div
        v-else-if="!cards.data?.length"
        class="executive-card flex flex-col items-center gap-3 p-10 text-center"
      >
        <LucideFileText class="size-8 text-ink-gray-4" />
        <div class="text-base font-medium text-ink-gray-8">
          {{ search || status ? __("No job cards match") : __("No job cards yet") }}
        </div>
        <p class="max-w-md text-sm text-ink-gray-6">
          {{
            __(
              "A job card records the work done for a client: what was asked, what was done, the time it took. Print it for the client to sign, or let them sign it in their portal. Open one from a ticket's sidebar, or here."
            )
          }}
        </p>
      </div>

      <div v-else class="executive-card overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="border-b border-outline-gray-2 text-left text-xs text-ink-gray-5">
            <tr>
              <th class="px-4 py-2.5 font-medium">{{ __("Number") }}</th>
              <th class="px-4 py-2.5 font-medium">{{ __("Date") }}</th>
              <th class="px-4 py-2.5 font-medium">{{ __("Client") }}</th>
              <th class="px-4 py-2.5 font-medium">{{ __("Ticket") }}</th>
              <th class="px-4 py-2.5 font-medium">{{ __("Technician") }}</th>
              <th class="px-4 py-2.5 text-right font-medium">{{ __("Hours") }}</th>
              <th class="px-4 py-2.5 font-medium">{{ __("Status") }}</th>
              <th class="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-gray-1">
            <tr
              v-for="c in cards.data"
              :key="c.name"
              class="cursor-pointer hover:bg-surface-gray-1"
              @click="openCard(c.name)"
            >
              <td class="whitespace-nowrap px-4 py-2.5 font-medium text-ink-gray-9">{{ c.name }}</td>
              <td class="whitespace-nowrap px-4 py-2.5 text-ink-gray-7">{{ longDate(c.date) }}</td>
              <td class="px-4 py-2.5 text-ink-gray-8">{{ c.customer }}</td>
              <td class="whitespace-nowrap px-4 py-2.5">
                <RouterLink
                  v-if="c.ticket"
                  :to="{ name: 'TicketAgent', params: { ticketId: c.ticket } }"
                  class="text-ink-gray-7 hover:underline"
                  @click.stop
                >
                  #{{ c.ticket }}
                </RouterLink>
              </td>
              <td class="px-4 py-2.5 text-ink-gray-7">{{ c.technician_name }}</td>
              <td class="whitespace-nowrap px-4 py-2.5 text-right text-ink-gray-8">
                {{ fmt(c.total_hours) }}
              </td>
              <td class="px-4 py-2.5">
                <Badge variant="subtle" :label="__(c.status)" :theme="statusTheme(c.status)" />
              </td>
              <td class="px-4 py-2.5 text-right">
                <Button
                  size="sm"
                  variant="ghost"
                  :aria-label="__('Print {0}', [c.name])"
                  :title="__('Print')"
                  @click.stop="printJobCard(c.name)"
                >
                  <LucidePrinter class="size-3.5" />
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <JobCardDialog v-model="showCard" :name="cardName" @changed="onChanged" />

    <Dialog v-model="showSettings" :options="{ title: __('Job card print settings'), size: 'lg' }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <FormControl
            v-model="footer"
            type="textarea"
            :rows="4"
            :label="__('Footer')"
            :placeholder="__('Company address, phone, website, payment or service terms')"
          />
          <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8">
            <input v-model="showUsage" type="checkbox" class="size-4 accent-blue-600" />
            {{ __("Print the client's support plan balance on the card") }}
          </label>
        </div>
      </template>
      <template #actions>
        <div class="flex w-full justify-end gap-2">
          <Button :label="__('Cancel')" @click="showSettings = false" />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="settingsSave.loading"
            @click="saveSettings"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  dayjs,
  toast,
  usePageMeta,
} from "frappe-ui";
import { LayoutHeader } from "@/components";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucideFileText from "~icons/lucide/file-text";
import LucidePlus from "~icons/lucide/plus";
import LucidePrinter from "~icons/lucide/printer";
import JobCardDialog from "@/components/jobcards/JobCardDialog.vue";
import { printJobCard } from "@/components/jobcards/print";

usePageMeta(() => ({ title: __("Job cards") }));

const authStore = useAuthStore();
const isManager = computed(() => !!authStore.isManager);

const STATUS_OPTIONS = [
  { label: __("Any status"), value: "" },
  { label: __("Open"), value: "Open" },
  { label: __("Completed"), value: "Completed" },
  { label: __("Signed"), value: "Signed" },
  { label: __("Cancelled"), value: "Cancelled" },
];

const search = ref("");
const status = ref("");

const cards = createResource({
  url: "helpdesk.api.job_card.list_job_cards",
  makeParams: () => ({ search: search.value.trim() || null, status: status.value || null }),
  auto: true,
});

let typing: ReturnType<typeof setTimeout> | undefined;
watch([search, status], () => {
  clearTimeout(typing);
  typing = setTimeout(() => cards.reload(), 300);
});

const showCard = ref(false);
const cardName = ref<string | null>(null);

function openCard(name: string | null) {
  cardName.value = name;
  showCard.value = true;
}

function onChanged(name: string | null) {
  if (name) cardName.value = name;
  cards.reload();
}

// Print settings (managers)
const showSettings = ref(false);
const footer = ref("");
const showUsage = ref(true);
const settingsLoad = createResource({
  url: "helpdesk.api.job_card.get_print_settings",
  onError: () => {},
});
const settingsSave = createResource({
  url: "helpdesk.api.job_card.save_print_settings",
  onError: () => {},
});

async function openSettings() {
  try {
    const s = await settingsLoad.submit();
    footer.value = s.footer || "";
    showUsage.value = !!s.show_contract_usage;
    showSettings.value = true;
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not load the print settings"));
  }
}

async function saveSettings() {
  try {
    await settingsSave.submit({
      footer: footer.value,
      show_contract_usage: showUsage.value ? 1 : 0,
    });
    toast.success(__("Print settings saved"));
    showSettings.value = false;
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the print settings"));
  }
}

function statusTheme(s: string) {
  return ({ Signed: "green", Completed: "blue", Cancelled: "red" } as Record<string, string>)[s] || "gray";
}

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

function longDate(d: string) {
  return d ? dayjs(d).format("D MMM YYYY") : "";
}
</script>
