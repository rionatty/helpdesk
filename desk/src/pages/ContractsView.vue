<template>
  <div class="flex h-full flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideTimer class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Support contracts") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <Button
          v-if="isManager"
          variant="solid"
          :label="__('New contract')"
          @click="openEditor()"
        >
          <template #prefix><LucidePlus class="size-4" /></template>
        </Button>
      </template>
    </LayoutHeader>

    <div
      class="mx-auto flex w-full max-w-screen-2xl flex-1 flex-col gap-4 overflow-y-auto px-4 py-6 md:px-6 lg:px-8"
    >
      <div class="flex flex-wrap items-center gap-3">
        <FormControl
          v-model="search"
          class="w-full sm:w-72"
          type="text"
          :placeholder="__('Search clients or contracts')"
          :aria-label="__('Search clients or contracts')"
        />
        <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7">
          <input
            v-model="showInactive"
            type="checkbox"
            class="size-4 accent-blue-600"
          />
          {{ __("Show ended and cancelled") }}
        </label>
        <span class="flex-1" />
        <div class="flex flex-wrap gap-2 text-sm">
          <span class="rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-ink-gray-7">
            {{ __("{0} in force", [counts.inForce]) }}
          </span>
          <span
            v-if="counts.near"
            class="rounded-full bg-amber-100 px-2.5 py-0.5 text-amber-800"
          >
            {{ __("{0} near their limit", [counts.near]) }}
          </span>
          <span
            v-if="counts.over"
            class="rounded-full bg-red-100 px-2.5 py-0.5 text-red-800"
          >
            {{ __("{0} over their hours", [counts.over]) }}
          </span>
        </div>
      </div>

      <div
        v-if="contracts.loading && !contracts.data"
        class="py-16 text-center text-sm text-ink-gray-5"
      >
        {{ __("Loading...") }}
      </div>

      <div
        v-else-if="!rows.length"
        class="executive-card flex flex-col items-center gap-3 p-10 text-center"
      >
        <LucideTimer class="size-8 text-ink-gray-4" />
        <div class="text-base font-medium text-ink-gray-8">
          {{
            contracts.data?.length
              ? __("No contracts match")
              : __("No support contracts yet")
          }}
        </div>
        <p class="max-w-md text-sm text-ink-gray-6">
          {{
            __(
              "A contract gives a client a number of support hours each month, quarter or year. Time logged on their tickets counts against it, and they see the balance on their portal."
            )
          }}
        </p>
        <Button
          v-if="isManager && !contracts.data?.length"
          variant="solid"
          :label="__('New contract')"
          @click="openEditor()"
        />
      </div>

      <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
        <div
          v-for="c in rows"
          :key="c.name"
          class="executive-card flex flex-col gap-3 p-4"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div
                class="truncate text-base font-semibold text-ink-gray-9"
                :title="c.customer"
              >
                {{ c.customer }}
              </div>
              <div class="truncate text-sm text-ink-gray-6" :title="c.contract_name">
                {{ c.contract_name }}
              </div>
            </div>
            <Badge
              class="shrink-0"
              variant="subtle"
              :label="__(c.state)"
              :theme="stateTheme(c.state)"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <div class="flex items-baseline justify-between gap-2 text-sm">
              <span class="text-ink-gray-7">{{ c.period_label }}</span>
              <span class="font-medium text-ink-gray-9">
                {{ __("{0} of {1} h", [fmt(c.used), fmt(c.included)]) }}
              </span>
            </div>
            <div class="h-2 overflow-hidden rounded-full bg-surface-gray-2">
              <div
                class="h-full rounded-full"
                :class="barClass(c)"
                :style="{ width: barWidth(c) }"
              />
            </div>
            <div class="flex items-center justify-between gap-2 text-xs">
              <span class="text-ink-gray-5">{{ periodNote(c) }}</span>
              <span :class="leftClass(c)">{{ leftLabel(c) }}</span>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2 pt-1">
            <Button
              size="sm"
              variant="subtle"
              :label="__('Statement')"
              @click="openStatement(c)"
            >
              <template #prefix><LucideFileText class="size-3.5" /></template>
            </Button>
            <Button
              v-if="c.state === 'In force'"
              size="sm"
              variant="subtle"
              :label="__('Log time')"
              @click="openLog(c)"
            >
              <template #prefix><LucideClock class="size-3.5" /></template>
            </Button>
            <span class="flex-1" />
            <Button
              v-if="isManager"
              size="sm"
              variant="ghost"
              :aria-label="__('Edit contract')"
              :title="__('Edit contract')"
              @click="openEditor(c)"
            >
              <LucidePencil class="size-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- New / edit contract -->
    <Dialog
      v-model="showEditor"
      :options="{
        title: editor.name ? __('Edit contract') : __('New contract'),
        size: 'xl',
      }"
    >
      <template #body-content>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div class="sm:col-span-2">
            <Link
              v-model="editor.customer"
              doctype="HD Customer"
              :label="__('Client')"
              :placeholder="__('Pick a client')"
            />
          </div>
          <FormControl
            v-model="editor.contract_name"
            class="sm:col-span-2"
            :label="__('Contract name')"
            :placeholder="__('e.g. SAP Business One support, 10 h a month')"
          />
          <FormControl
            v-model="editor.period"
            type="select"
            :options="PERIOD_OPTIONS"
            :label="__('Hours renew')"
          />
          <FormControl
            v-model="editor.hours_per_period"
            type="number"
            min="0.5"
            step="0.5"
            :label="__('Included hours')"
          />
          <FormControl v-model="editor.start_date" type="date" :label="__('Starts')" />
          <FormControl
            v-model="editor.end_date"
            type="date"
            :label="__('Ends (leave empty if open-ended)')"
          />
          <FormControl
            v-model="editor.alert_at_percent"
            type="number"
            min="1"
            max="100"
            :label="__('Email managers at (% used)')"
          />
          <FormControl
            v-model="editor.status"
            type="select"
            :options="STATUS_OPTIONS"
            :label="__('Status')"
          />
          <FormControl
            v-model="editor.notes"
            class="sm:col-span-2"
            type="textarea"
            :rows="2"
            :label="__('Internal notes')"
            :placeholder="__('Only the team sees these')"
          />
        </div>
      </template>
      <template #actions>
        <div class="flex w-full items-center gap-2">
          <Button
            v-if="editor.name"
            variant="ghost"
            theme="red"
            :label="armedDelete ? __('Click again to delete') : __('Delete')"
            :loading="deleteRes.loading"
            @click="removeContract"
          />
          <span class="flex-1" />
          <Button :label="__('Cancel')" @click="showEditor = false" />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saveRes.loading"
            @click="saveContract"
          />
        </div>
      </template>
    </Dialog>

    <!-- Log time on a contract (work outside tickets) -->
    <Dialog
      v-model="showLog"
      :options="{ title: __('Log time: {0}', [logFor?.customer || '']), size: 'md' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3">
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                "For work outside a ticket, such as a call or a training session. Time spent on a ticket is logged on the ticket."
              )
            }}
          </p>
          <div class="grid grid-cols-2 gap-3">
            <FormControl
              v-model="logForm.hours"
              type="number"
              step="0.25"
              min="0.25"
              max="24"
              :label="__('Hours')"
            />
            <FormControl
              v-model="logForm.day"
              type="date"
              :max="today"
              :label="__('Date')"
            />
          </div>
          <FormControl
            v-model="logForm.description"
            type="textarea"
            :rows="3"
            :label="__('What was done')"
            :placeholder="__('The client sees this on their statement')"
          />
          <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7">
            <input
              v-model="logForm.billable"
              type="checkbox"
              class="size-4 accent-blue-600"
            />
            {{ __("Billable: counts against the contract") }}
          </label>
        </div>
      </template>
      <template #actions>
        <div class="flex w-full justify-end gap-2">
          <Button :label="__('Cancel')" @click="showLog = false" />
          <Button
            variant="solid"
            :label="__('Log time')"
            :disabled="!logValid"
            :loading="logRes.loading"
            @click="submitLog"
          />
        </div>
      </template>
    </Dialog>

    <!-- Statement -->
    <Dialog v-model="showStatement" :options="{ title: __('Statement'), size: '4xl' }">
      <template #body-content>
        <div
          v-if="!statement.data"
          class="py-10 text-center text-sm text-ink-gray-5"
        >
          {{ __("Loading...") }}
        </div>
        <div v-else class="flex flex-col gap-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate text-base font-semibold text-ink-gray-9">
                {{ statement.data.customer }}
              </div>
              <div class="truncate text-sm text-ink-gray-6">
                {{ statement.data.contract_name }}
              </div>
            </div>
            <div class="flex items-center gap-1">
              <Button
                size="sm"
                variant="ghost"
                :disabled="!statement.data.has_previous || statement.loading"
                :aria-label="__('Previous period')"
                @click="page(-1)"
              >
                <LucideChevronLeft class="size-4" />
              </Button>
              <span class="min-w-[9rem] text-center text-sm font-medium text-ink-gray-8">
                {{ statement.data.period_label }}
              </span>
              <Button
                size="sm"
                variant="ghost"
                :disabled="!statement.data.has_next || statement.loading"
                :aria-label="__('Next period')"
                @click="page(1)"
              >
                <LucideChevronRight class="size-4" />
              </Button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-md bg-surface-gray-1 p-3">
              <div class="text-xs text-ink-gray-5">{{ __("Included") }}</div>
              <div class="text-lg font-semibold text-ink-gray-9">
                {{ fmt(statement.data.included) }} h
              </div>
            </div>
            <div class="rounded-md bg-surface-gray-1 p-3">
              <div class="text-xs text-ink-gray-5">{{ __("Used (billable)") }}</div>
              <div class="text-lg font-semibold text-ink-gray-9">
                {{ fmt(statement.data.used) }} h
                <span class="text-sm font-normal text-ink-gray-5">
                  {{ statement.data.pct }}%
                </span>
              </div>
            </div>
            <div class="rounded-md bg-surface-gray-1 p-3">
              <div class="text-xs text-ink-gray-5">
                {{ statement.data.remaining >= 0 ? __("Left") : __("Over") }}
              </div>
              <div
                class="text-lg font-semibold"
                :class="statement.data.remaining >= 0 ? 'text-ink-gray-9' : 'text-ink-red-3'"
              >
                {{ fmt(Math.abs(statement.data.remaining)) }} h
              </div>
            </div>
            <div class="rounded-md bg-surface-gray-1 p-3">
              <div class="text-xs text-ink-gray-5">{{ __("Not billable") }}</div>
              <div class="text-lg font-semibold text-ink-gray-9">
                {{ fmt(statement.data.non_billable) }} h
              </div>
            </div>
          </div>

          <div class="overflow-x-auto rounded-md ring-1 ring-outline-gray-2">
            <table class="w-full text-sm">
              <thead class="bg-surface-gray-1 text-left text-xs text-ink-gray-6">
                <tr>
                  <th class="px-3 py-2 font-medium">{{ __("Date") }}</th>
                  <th class="px-3 py-2 font-medium">{{ __("Hours") }}</th>
                  <th class="px-3 py-2 font-medium">{{ __("Billable") }}</th>
                  <th class="px-3 py-2 font-medium">{{ __("Work") }}</th>
                  <th class="px-3 py-2 font-medium">{{ __("By") }}</th>
                  <th class="px-3 py-2" />
                </tr>
              </thead>
              <tbody class="divide-y divide-outline-gray-1">
                <tr
                  v-for="l in statement.data.logs"
                  :key="l.name"
                  :class="l.billable ? 'text-ink-gray-8' : 'text-ink-gray-5'"
                >
                  <td class="whitespace-nowrap px-3 py-2">{{ longDate(l.date) }}</td>
                  <td class="whitespace-nowrap px-3 py-2 font-medium">{{ fmt(l.hours) }}</td>
                  <td class="px-3 py-2">
                    <input
                      type="checkbox"
                      class="size-4 accent-blue-600"
                      :checked="!!l.billable"
                      :disabled="!l.can_change || billableRes.loading"
                      :aria-label="__('Billable')"
                      @change="toggleBillable(l, $event)"
                    />
                  </td>
                  <td class="min-w-[16rem] px-3 py-2">
                    <div>{{ workText(l) }}</div>
                    <RouterLink
                      v-if="l.ticket"
                      :to="{ name: 'TicketAgent', params: { ticketId: l.ticket } }"
                      class="text-xs text-ink-gray-5 hover:underline"
                    >
                      #{{ l.ticket }} {{ l.ticket_subject }}
                    </RouterLink>
                  </td>
                  <td class="whitespace-nowrap px-3 py-2 text-ink-gray-6">
                    {{ l.logged_by_name }}
                  </td>
                  <td class="px-3 py-2 text-right">
                    <Button
                      v-if="l.can_delete"
                      size="sm"
                      variant="ghost"
                      :aria-label="__('Remove this entry')"
                      :title="__('Remove this entry')"
                      @click="removeLog(l)"
                    >
                      <LucideTrash2 class="size-3.5" />
                    </Button>
                  </td>
                </tr>
                <tr v-if="!statement.data.logs.length">
                  <td colspan="6" class="px-3 py-8 text-center text-ink-gray-5">
                    {{ __("No time logged in this period.") }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex w-full items-center gap-2">
          <Button
            :label="__('Download CSV')"
            :disabled="!statement.data?.logs?.length"
            @click="downloadCsv"
          >
            <template #prefix><LucideDownload class="size-4" /></template>
          </Button>
          <span class="flex-1" />
          <Button
            v-if="statement.data?.state === 'In force'"
            variant="solid"
            :label="__('Log time')"
            @click="openLog(statement.data)"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
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
import { LayoutHeader, Link } from "@/components";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucideTimer from "~icons/lucide/timer";
import LucidePlus from "~icons/lucide/plus";
import LucidePencil from "~icons/lucide/pencil";
import LucideClock from "~icons/lucide/clock";
import LucideFileText from "~icons/lucide/file-text";
import LucideDownload from "~icons/lucide/download";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideChevronLeft from "~icons/lucide/chevron-left";
import LucideChevronRight from "~icons/lucide/chevron-right";

usePageMeta(() => ({ title: __("Support contracts") }));

const authStore = useAuthStore();
const isManager = computed(() => !!authStore.isManager);

const PERIOD_OPTIONS = [
  { label: __("Every month"), value: "Monthly" },
  { label: __("Every quarter"), value: "Quarterly" },
  { label: __("Every contract year"), value: "Yearly" },
  { label: __("Once, for the whole contract"), value: "Whole contract" },
];
const STATUS_OPTIONS = [
  { label: __("Active"), value: "Active" },
  { label: __("Expired"), value: "Expired" },
  { label: __("Cancelled"), value: "Cancelled" },
];

const today = dayjs().format("YYYY-MM-DD");

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

const contracts = createResource({
  url: "helpdesk.api.contracts.list_contracts",
  auto: true,
});

const search = ref("");
const showInactive = ref(false);

const rows = computed<any[]>(() => {
  const q = search.value.trim().toLowerCase();
  return (contracts.data || []).filter(
    (c: any) =>
      (showInactive.value || ["In force", "Not started"].includes(c.state)) &&
      (!q ||
        (c.customer || "").toLowerCase().includes(q) ||
        (c.contract_name || "").toLowerCase().includes(q))
  );
});

const counts = computed(() => {
  const live = (contracts.data || []).filter((c: any) => c.state === "In force");
  return {
    inForce: live.length,
    near: live.filter((c: any) => c.pct >= c.alert_at && c.pct < 100).length,
    over: live.filter((c: any) => c.pct >= 100).length,
  };
});

function stateTheme(state: string) {
  if (state === "In force") return "green";
  if (state === "Not started") return "blue";
  if (state === "Cancelled") return "red";
  return "gray";
}

function periodNote(c: any) {
  if (c.state === "Not started") return __("Starts {0}", [longDate(c.start_date)]);
  if (c.state !== "In force") {
    return c.end_date ? __("Ended {0}", [longDate(c.end_date)]) : "";
  }
  if (c.period === "Whole contract") {
    return c.end_date ? __("Runs to {0}", [longDate(c.end_date)]) : __("No end date");
  }
  const renews = dayjs(c.period_to).add(1, "day");
  if (c.end_date && renews.isAfter(dayjs(c.end_date))) {
    return __("Contract ends {0}", [longDate(c.end_date)]);
  }
  return __("Renews {0}", [longDate(renews.format("YYYY-MM-DD"))]);
}

// ---------------------------------------------------------------------------
// New / edit contract (managers)
// ---------------------------------------------------------------------------

const showEditor = ref(false);
const armedDelete = ref(false);
const editor = reactive<Record<string, any>>({});

function blankContract() {
  return {
    name: null,
    customer: "",
    contract_name: "",
    status: "Active",
    period: "Monthly",
    hours_per_period: 10,
    start_date: dayjs().startOf("month").format("YYYY-MM-DD"),
    end_date: "",
    alert_at_percent: 80,
    notes: "",
  };
}

function openEditor(c?: any) {
  const base = blankContract();
  Object.assign(
    editor,
    base,
    c
      ? Object.fromEntries(Object.keys(base).map((k) => [k, c[k] ?? (base as any)[k]]))
      : {}
  );
  if (c && !c.end_date) editor.end_date = "";
  armedDelete.value = false;
  showEditor.value = true;
}

const saveRes = createResource({
  url: "helpdesk.api.contracts.save_contract",
  onError: () => {},
});
async function saveContract() {
  try {
    await saveRes.submit({
      data: {
        ...editor,
        hours_per_period: Number(editor.hours_per_period) || 0,
        alert_at_percent: Number(editor.alert_at_percent) || 80,
      },
    });
    toast.success(__("Contract saved"));
    showEditor.value = false;
    contracts.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the contract"));
  }
}

const deleteRes = createResource({
  url: "helpdesk.api.contracts.delete_contract",
  onError: () => {},
});
let disarm: ReturnType<typeof setTimeout> | undefined;
async function removeContract() {
  if (!armedDelete.value) {
    armedDelete.value = true;
    clearTimeout(disarm);
    disarm = setTimeout(() => (armedDelete.value = false), 4000);
    return;
  }
  armedDelete.value = false;
  try {
    await deleteRes.submit({ name: editor.name });
    toast.success(__("Contract deleted. The time logged for the client is kept."));
    showEditor.value = false;
    contracts.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not delete the contract"));
  }
}

// ---------------------------------------------------------------------------
// Log time on a contract
// ---------------------------------------------------------------------------

const showLog = ref(false);
const logFor = ref<any>(null);
const logForm = reactive({
  hours: 1 as number | string,
  day: today,
  description: "",
  billable: true,
});
const logValid = computed(() => {
  const h = Number(logForm.hours);
  return h > 0 && h <= 24 && logForm.description.trim().length > 0;
});

function openLog(c: any) {
  logFor.value = c;
  Object.assign(logForm, { hours: 1, day: today, description: "", billable: true });
  showLog.value = true;
}

const logRes = createResource({
  url: "helpdesk.api.contracts.log_time",
  onError: () => {},
});
async function submitLog() {
  if (!logValid.value || !logFor.value) return;
  try {
    await logRes.submit({
      contract: logFor.value.name,
      hours: Number(logForm.hours),
      day: logForm.day || today,
      description: logForm.description.trim(),
      billable: logForm.billable ? 1 : 0,
    });
    toast.success(__("Logged {0} h", [fmt(Number(logForm.hours))]));
    showLog.value = false;
    contracts.reload();
    if (showStatement.value) statement.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not log the time"));
  }
}

// ---------------------------------------------------------------------------
// Statement
// ---------------------------------------------------------------------------

const showStatement = ref(false);
const statementFor = ref<{ contract: string; on: string | null }>({
  contract: "",
  on: null,
});
const statement = createResource({
  url: "helpdesk.api.contracts.get_statement",
  makeParams: () => statementFor.value,
  onError: (e: any) => {
    toast.error(e?.messages?.[0] || __("Could not load the statement"));
    showStatement.value = false;
  },
});

function openStatement(c: any) {
  statementFor.value = { contract: c.name, on: null };
  statement.data = null;
  showStatement.value = true;
  statement.reload();
}

function page(step: number) {
  const d = statement.data;
  if (!d) return;
  const on =
    step < 0
      ? dayjs(d.period_from).subtract(1, "day")
      : dayjs(d.period_to).add(1, "day");
  statementFor.value = { contract: d.name, on: on.format("YYYY-MM-DD") };
  statement.reload();
}

const billableRes = createResource({
  url: "helpdesk.api.contracts.set_billable",
  onError: () => {},
});
async function toggleBillable(l: any, event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  try {
    await billableRes.submit({ name: l.name, billable: checked ? 1 : 0 });
    statement.reload();
    contracts.reload();
  } catch (e: any) {
    (event.target as HTMLInputElement).checked = !checked;
    toast.error(e?.messages?.[0] || __("Could not change the entry"));
  }
}

const removeRes = createResource({
  url: "helpdesk.api.contracts.delete_time_log",
  onError: () => {},
});
async function removeLog(l: any) {
  try {
    await removeRes.submit({ name: l.name });
    statement.reload();
    contracts.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not remove the entry"));
  }
}

function workText(l: any) {
  if (l.description) return l.description;
  if (l.subtask_subject) return l.subtask_subject;
  return l.ticket ? __("Work on the ticket") : "";
}

// Spreadsheet apps run a cell that starts with = + - @ as a formula, and
// ticket subjects come from customers: such cells are prefixed with '.
function csvCell(value: any) {
  let s = value == null ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return `"${s.replace(/"/g, '""')}"`;
}

function downloadCsv() {
  const d = statement.data;
  if (!d) return;
  const lines = [
    [
      __("Date"),
      __("Hours"),
      __("Billable"),
      __("Work"),
      __("Ticket"),
      __("Ticket subject"),
      __("Logged by"),
    ],
    ...d.logs.map((l: any) => [
      l.date,
      fmt(l.hours),
      l.billable ? __("Yes") : __("No"),
      workText(l),
      l.ticket || "",
      l.ticket_subject || "",
      l.logged_by_name || "",
    ]),
    [],
    [__("Included"), fmt(d.included)],
    [__("Used (billable)"), fmt(d.used)],
    [d.remaining >= 0 ? __("Left") : __("Over"), fmt(Math.abs(d.remaining))],
    [__("Not billable"), fmt(d.non_billable)],
  ];
  const csv = "﻿" + lines.map((r) => r.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${d.customer} ${d.period_label}.csv`.replace(/[\\/:*?"<>|]+/g, "-");
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

function longDate(d: string) {
  return d ? dayjs(d).format("D MMM YYYY") : "";
}

function barWidth(u: any) {
  return `${Math.min(100, Math.max(0, u.pct || 0))}%`;
}

function barClass(u: any) {
  if (u.pct >= 100) return "bg-red-500";
  if (u.pct >= u.alert_at) return "bg-amber-500";
  return "bg-emerald-500";
}

function leftLabel(u: any) {
  return u.remaining >= 0
    ? __("{0} h left", [fmt(u.remaining)])
    : __("{0} h over", [fmt(-u.remaining)]);
}

function leftClass(u: any) {
  if (u.remaining < 0) return "font-medium text-ink-red-3";
  if (u.pct >= u.alert_at) return "font-medium text-ink-amber-3";
  return "text-ink-gray-6";
}
</script>
