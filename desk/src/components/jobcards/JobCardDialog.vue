<template>
  <Dialog
    v-model="open"
    :options="{
      title: card?.name ? __('Job card {0}', [card.name]) : __('New job card'),
      size: '4xl',
    }"
  >
    <template #body-content>
      <div v-if="!card" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __("Loading...") }}
      </div>
      <div v-else class="flex flex-col gap-5">
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="subtle" :label="__(card.status)" :theme="statusTheme(card.status)" />
          <span v-if="card.ticket" class="text-ink-gray-6">
            #{{ card.ticket }} {{ card.ticket_subject }}
          </span>
          <span v-if="card.status === 'Signed'" class="text-ink-gray-6">
            · {{ __("Signed by {0}", [card.signed_by]) }}
          </span>
        </div>
        <p
          v-if="!card.can_edit"
          class="rounded-md bg-surface-gray-1 p-3 text-p-sm text-ink-gray-7"
        >
          {{
            card.status === "Cancelled"
              ? __("This job card is cancelled.")
              : __("This job card is signed, so it can no longer be changed. You can still print it.")
          }}
        </p>

        <!-- Client and job -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="sm:col-span-1">
            <Link
              v-model="card.customer"
              doctype="HD Customer"
              :label="__('Client')"
              :placeholder="__('Pick a client')"
              :disabled="!card.can_edit"
            />
          </div>
          <FormControl
            v-model="card.date"
            type="date"
            :label="__('Date')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.service_type"
            type="select"
            :options="SERVICE_OPTIONS"
            :label="__('Service')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-if="card.service_type === 'On-site'"
            v-model="card.location"
            :label="__('Location')"
            :placeholder="__('Where the work was done')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.time_in"
            type="time"
            :label="__('Time in')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.time_out"
            type="time"
            :label="__('Time out')"
            :disabled="!card.can_edit"
          />
          <div>
            <Link
              v-model="card.technician"
              doctype="HD Agent"
              :label="__('Technician')"
              :disabled="!card.can_edit"
            />
          </div>
        </div>

        <!-- Client contact -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <FormControl
            v-model="card.contact_name"
            :label="__('Client contact')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.contact_phone"
            :label="__('Phone')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.contact_email"
            :label="__('Email')"
            :disabled="!card.can_edit"
          />
        </div>

        <!-- The work -->
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormControl
            v-model="card.work_requested"
            type="textarea"
            :rows="4"
            :label="__('Work requested')"
            :placeholder="__('The problem reported, or the work asked for')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.work_done"
            type="textarea"
            :rows="4"
            :label="__('Work done')"
            :placeholder="__('What you did, in words the client understands')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.work_status"
            type="select"
            :options="OUTCOME_OPTIONS"
            :label="__('Outcome')"
            :disabled="!card.can_edit"
          />
          <FormControl
            v-model="card.recommendations"
            type="textarea"
            :rows="2"
            :label="__('Recommendations (optional)')"
            :placeholder="__('Next steps, advice, follow-up')"
            :disabled="!card.can_edit"
          />
        </div>

        <!-- Time spent -->
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-semibold text-ink-gray-8">{{ __("Time spent") }}</span>
            <span class="text-sm text-ink-gray-7">
              {{ __("Total {0} h", [fmt(total)]) }}
            </span>
          </div>
          <div
            v-if="card.lines.length"
            class="flex flex-col divide-y divide-outline-gray-1 rounded-md border border-outline-gray-1"
          >
            <div
              v-for="(line, i) in card.lines"
              :key="line.key"
              class="grid grid-cols-[8.5rem_5rem_1fr_auto] items-start gap-2 p-2"
            >
              <FormControl
                v-model="line.date"
                type="date"
                :disabled="!card.can_edit"
                :aria-label="__('Date')"
              />
              <FormControl
                v-model="line.hours"
                type="number"
                step="0.25"
                min="0.25"
                max="24"
                :disabled="!card.can_edit"
                :aria-label="__('Hours')"
              />
              <div class="flex min-w-0 flex-col gap-0.5">
                <FormControl
                  v-model="line.description"
                  :placeholder="__('What was done')"
                  :disabled="!card.can_edit"
                  :aria-label="__('Work')"
                />
                <span class="px-1 text-xs text-ink-gray-5">
                  {{ line.technician_name }}
                  <template v-if="line.time_log && !line.from_card">
                    · {{ __("from the ticket's logged time") }}
                  </template>
                </span>
              </div>
              <Button
                v-if="card.can_edit"
                variant="ghost"
                :aria-label="__('Remove line')"
                :title="__('Remove line')"
                @click="card.lines.splice(i, 1)"
              >
                <LucideTrash2 class="size-3.5" />
              </Button>
            </div>
          </div>
          <p v-else class="text-p-sm text-ink-gray-5">
            {{ __("No time on this card yet.") }}
          </p>
          <div v-if="card.can_edit" class="flex flex-wrap items-center justify-between gap-2">
            <Button size="sm" variant="subtle" :label="__('Add time')" @click="addLine">
              <template #prefix><LucidePlus class="size-3.5" /></template>
            </Button>
            <label class="flex cursor-pointer items-center gap-2 text-xs text-ink-gray-7">
              <input v-model="logTime" type="checkbox" class="size-3.5 accent-blue-600" />
              {{ __("Count new time in the client's support hours") }}
            </label>
          </div>
        </div>

        <!-- Items used -->
        <div class="flex flex-col gap-2">
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Items used (optional)") }}
          </span>
          <div
            v-for="(item, i) in card.items"
            :key="item.key"
            class="grid grid-cols-[1fr_6rem_auto] items-center gap-2"
          >
            <FormControl
              v-model="item.description"
              maxlength="140"
              :placeholder="__('e.g. Toner cartridge')"
              :disabled="!card.can_edit"
              :aria-label="__('Item')"
            />
            <FormControl
              v-model="item.quantity"
              type="number"
              min="0"
              :disabled="!card.can_edit"
              :aria-label="__('Quantity')"
            />
            <Button
              v-if="card.can_edit"
              variant="ghost"
              :aria-label="__('Remove item')"
              @click="card.items.splice(i, 1)"
            >
              <LucideTrash2 class="size-3.5" />
            </Button>
          </div>
          <Button
            v-if="card.can_edit"
            class="self-start"
            size="sm"
            variant="subtle"
            :label="__('Add item')"
            @click="addItem"
          >
            <template #prefix><LucidePlus class="size-3.5" /></template>
          </Button>
        </div>
      </div>
    </template>
    <template #actions>
      <div v-if="card" class="flex w-full flex-wrap items-center gap-2">
        <Button
          v-if="card.name && card.can_edit"
          variant="ghost"
          theme="red"
          :label="armed ? __('Click again to delete') : __('Delete')"
          :loading="deleteRes.loading"
          @click="remove"
        />
        <Button
          v-if="card.name && card.can_cancel && card.status === 'Signed'"
          variant="ghost"
          theme="red"
          :label="armed ? __('Click again to cancel the card') : __('Cancel card')"
          @click="cancelCard"
        />
        <span class="flex-1" />
        <Button
          v-if="card.name"
          :label="__('Print')"
          @click="printSaved"
        >
          <template #prefix><LucidePrinter class="size-4" /></template>
        </Button>
        <template v-if="card.can_edit">
          <Button
            v-if="card.name && card.status === 'Open'"
            :label="__('Mark completed')"
            :loading="statusRes.loading"
            @click="setStatus('Completed')"
          />
          <Button
            v-if="card.status === 'Completed'"
            :label="__('Reopen')"
            :loading="statusRes.loading"
            @click="setStatus('Open')"
          />
          <Button
            v-if="card.name"
            :label="__('Client sign-off')"
            @click="startSign"
          />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saveRes.loading"
            @click="save()"
          />
        </template>
      </div>
    </template>
  </Dialog>

  <JobCardSignDialog
    v-if="card?.name"
    v-model="showSign"
    :card="card"
    agent-mode
    @signed="onSigned"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Badge, Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { Link } from "@/components";
import { __ } from "@/translation";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucidePrinter from "~icons/lucide/printer";
import JobCardSignDialog from "./JobCardSignDialog.vue";
import { printJobCard } from "./print";

const props = defineProps<{
  name?: string | null;
  ticket?: string | null;
  customer?: string | null;
}>();
const open = defineModel<boolean>({ default: false });
// Saving can log or remove time: the ticket's other panels refresh.
const emit = defineEmits<{ (e: "changed", name: string | null): void }>();

const SERVICE_OPTIONS = [
  { label: __("Remote"), value: "Remote" },
  { label: __("On-site"), value: "On-site" },
  { label: __("Phone"), value: "Phone" },
];
const OUTCOME_OPTIONS = [
  { label: __("Resolved"), value: "Resolved" },
  { label: __("Partly resolved"), value: "Partly resolved" },
  { label: __("Follow-up needed"), value: "Follow-up needed" },
];

let nextKey = 1;
const card = ref<any>(null);
const logTime = ref(true);
const armed = ref(false);
const showSign = ref(false);

const total = computed(() =>
  (card.value?.lines || []).reduce((sum: number, l: any) => sum + (Number(l.hours) || 0), 0)
);

// Frappe sends a Time field as "9:30:00"; a time input needs "09:30".
function hhmm(value: any) {
  const m = String(value || "").match(/^(\d{1,2}):(\d{2})/);
  return m ? `${m[1].padStart(2, "0")}:${m[2]}` : "";
}

function withKeys(data: any) {
  data.lines = (data.lines || []).map((l: any) => ({ ...l, key: nextKey++ }));
  data.items = (data.items || []).map((i: any) => ({ ...i, key: nextKey++ }));
  data.time_in = hhmm(data.time_in);
  data.time_out = hhmm(data.time_out);
  return data;
}

const loadRes = createResource({ url: "helpdesk.api.job_card.get_job_card", onError: () => {} });
const newRes = createResource({ url: "helpdesk.api.job_card.new_job_card", onError: () => {} });

async function load(name?: string | null) {
  card.value = null;
  armed.value = false;
  try {
    const data = name
      ? await loadRes.submit({ name })
      : await newRes.submit({ ticket: props.ticket || null, customer: props.customer || null });
    card.value = withKeys(data);
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not open the job card"));
    open.value = false;
  }
}

watch(open, (isOpen) => isOpen && load(props.name), { immediate: true });

function addLine() {
  card.value.lines.push({
    key: nextKey++,
    date: card.value.date,
    hours: 1,
    description: "",
    technician: card.value.technician,
    technician_name: "",
    time_log: null,
    from_card: 0,
  });
}

function addItem() {
  card.value.items.push({ key: nextKey++, description: "", quantity: 1 });
}

function statusTheme(status: string) {
  return ({ Signed: "green", Completed: "blue", Cancelled: "red" } as Record<string, string>)[status] || "gray";
}

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

const saveRes = createResource({ url: "helpdesk.api.job_card.save_job_card", onError: () => {} });

async function save(): Promise<string | null> {
  const c = card.value;
  if (!c.customer) {
    toast.error(__("Pick the client this job card is for"));
    return null;
  }
  try {
    const name = await saveRes.submit({
      data: {
        name: c.name,
        date: c.date,
        customer: c.customer,
        ticket: c.ticket,
        project: c.project,
        service_type: c.service_type,
        location: c.service_type === "On-site" ? c.location : "",
        time_in: c.time_in || null,
        time_out: c.time_out || null,
        technician: c.technician,
        contact: c.contact,
        contact_name: c.contact_name,
        contact_phone: c.contact_phone,
        contact_email: c.contact_email,
        work_requested: c.work_requested,
        work_done: c.work_done,
        work_status: c.work_status,
        recommendations: c.recommendations,
        log_time: logTime.value ? 1 : 0,
        lines: c.lines.map((l: any) => ({
          date: l.date,
          hours: Number(l.hours) || 0,
          description: l.description,
          technician: l.technician,
          time_log: l.time_log,
          from_card: l.from_card,
        })),
        items: c.items.map((i: any) => ({ description: i.description, quantity: Number(i.quantity) || 1 })),
      },
    });
    toast.success(__("Job card {0} saved", [name]));
    emit("changed", name);
    await load(name);
    return name;
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the job card"));
    return null;
  }
}

async function printSaved() {
  // Unsaved edits would not be on the printout: save first.
  const name = card.value.can_edit ? await save() : card.value.name;
  if (name) printJobCard(name);
}

async function startSign() {
  const name = await save();
  if (name) showSign.value = true;
}

function onSigned(updated: any) {
  card.value = withKeys(updated);
  emit("changed", updated.name);
}

const statusRes = createResource({ url: "helpdesk.api.job_card.set_status", onError: () => {} });
async function setStatus(status: string) {
  if (status === "Completed" && !(await save())) return;
  try {
    card.value = withKeys(await statusRes.submit({ name: card.value.name, status }));
    emit("changed", card.value.name);
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not change the job card"));
  }
}

let disarm: ReturnType<typeof setTimeout> | undefined;
function arm(): boolean {
  if (armed.value) {
    armed.value = false;
    return true;
  }
  armed.value = true;
  clearTimeout(disarm);
  disarm = setTimeout(() => (armed.value = false), 4000);
  return false;
}

const deleteRes = createResource({ url: "helpdesk.api.job_card.delete_job_card", onError: () => {} });
async function remove() {
  if (!arm()) return;
  try {
    await deleteRes.submit({ name: card.value.name });
    toast.success(__("Job card deleted"));
    emit("changed", null);
    open.value = false;
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not delete the job card"));
  }
}

async function cancelCard() {
  if (!arm()) return;
  try {
    card.value = withKeys(await statusRes.submit({ name: card.value.name, status: "Cancelled" }));
    emit("changed", card.value.name);
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not cancel the job card"));
  }
}
</script>
