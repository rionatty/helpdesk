<template>
  <div :class="isCustomerPortal ? 'bg-customer-portal min-h-full flex flex-col' : ''">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideBell class="size-5 text-ink-gray-7" />
          <span class="text-lg font-medium text-ink-gray-9">{{ __("Reminders") }}</span>
        </div>
      </template>
      <template #right-header>
        <Button theme="blue" variant="subtle" :label="__('New reminder')" @click="openCreate">
          <template #prefix><LucidePlus class="size-4" /></template>
        </Button>
      </template>
    </LayoutHeader>

    <div class="w-full max-w-screen-lg mx-auto px-4 md:px-6 py-6 flex flex-col gap-4 flex-1">

      <!-- Filter tabs -->
      <div class="flex gap-2 flex-wrap">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="px-3 py-1.5 text-sm rounded-lg font-medium transition-colors"
          :class="
            activeTab === tab.key
              ? 'bg-blue-600 text-white shadow-sm'
              : 'bg-surface-white border border-outline-gray-1 text-ink-gray-7 hover:bg-surface-gray-2'
          "
          @click="activeTab = tab.key"
        >
          {{ __(tab.label) }}
          <span v-if="tab.badge" class="ml-1 text-xs opacity-80">({{ tab.badge }})</span>
        </button>
      </div>

      <!-- Loading -->
      <div v-if="allRes.loading" class="flex-1 flex items-center justify-center py-20">
        <p class="text-sm text-ink-gray-5">{{ __("Loading…") }}</p>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="!filtered.length"
        class="flex-1 flex flex-col items-center justify-center gap-3 py-20"
      >
        <div class="size-16 rounded-full bg-surface-gray-2 flex items-center justify-center">
          <LucideBellOff class="size-8 text-ink-gray-4" />
        </div>
        <p class="text-sm text-ink-gray-5">{{ __("No reminders in this view.") }}</p>
        <Button
          v-if="activeTab === 'all' || activeTab === 'upcoming'"
          theme="blue"
          variant="subtle"
          :label="__('Create reminder')"
          @click="openCreate"
        />
      </div>

      <!-- Reminder cards -->
      <div v-else class="flex flex-col gap-2">
        <div
          v-for="r in filtered"
          :key="r.name"
          class="executive-card p-4 flex items-start gap-4"
          :class="isDue(r) ? 'ring-1 ring-red-200' : ''"
        >
          <!-- Status icon -->
          <div
            class="size-9 rounded-full flex items-center justify-center shrink-0 mt-0.5"
            :class="iconBg(r)"
          >
            <component :is="iconFor(r)" class="size-4" />
          </div>

          <!-- Body -->
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-ink-gray-9 break-words leading-snug">
              {{ r.message }}
            </p>
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
              <span
                class="text-xs"
                :class="isDue(r) ? 'text-red-500 font-semibold' : 'text-ink-gray-5'"
              >
                {{ fmtTime(r.remind_at) }}
              </span>
              <RouterLink
                v-if="r.reference_name"
                :to="refRoute(r)"
                class="text-xs text-blue-600 hover:underline flex items-center gap-0.5"
              >
                <LucideExternalLink class="size-3" />
                {{ r.reference_doctype }} · {{ r.reference_name }}
              </RouterLink>
              <Badge :label="r.status" :theme="statusTheme(r.status)" variant="subtle" />
              <span
                v-if="r.send_email"
                class="text-xs text-ink-gray-5 flex items-center gap-0.5"
              >
                <LucideMail class="size-3" />{{ __("Email") }}
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              v-if="r.status !== 'Performed' && r.status !== 'Dismissed'"
              class="size-8 rounded-lg flex items-center justify-center text-ink-gray-4 hover:bg-emerald-50 hover:text-emerald-600 transition-colors"
              :title="__('Mark as done')"
              @click="markDone(r.name)"
            >
              <LucideCheckCheck class="size-4" />
            </button>
            <button
              v-if="r.status !== 'Performed' && r.status !== 'Dismissed'"
              class="size-8 rounded-lg flex items-center justify-center text-ink-gray-4 hover:bg-blue-50 hover:text-blue-600 transition-colors"
              :title="__('Reschedule')"
              @click="openEdit(r)"
            >
              <LucideRefreshCw class="size-4" />
            </button>
            <button
              v-if="r.status !== 'Dismissed'"
              class="size-8 rounded-lg flex items-center justify-center text-ink-gray-4 hover:bg-red-50 hover:text-red-500 transition-colors"
              :title="__('Dismiss')"
              @click="dismissReminder(r.name)"
            >
              <LucideX class="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit dialog -->
    <Dialog
      v-if="showForm"
      v-model="showForm"
      :options="{
        title: editing ? __('Reschedule reminder') : __('New reminder'),
        size: 'sm',
      }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <!-- Reference — only when creating -->
          <template v-if="!editing">
            <div class="flex flex-col gap-1">
              <label class="text-xs font-medium text-ink-gray-6">
                {{ __("Linked to (optional)") }}
              </label>
              <select
                v-model="form.refDoctype"
                class="text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="form.refName = ''"
              >
                <option value="">{{ __("None") }}</option>
                <option value="HD Ticket">{{ __("Ticket") }}</option>
                <option value="HD Project">{{ __("Project") }}</option>
                <option value="HD Addon">{{ __("Add-on") }}</option>
                <option value="HD Task">{{ __("Task") }}</option>
              </select>
            </div>
            <div v-if="form.refDoctype" class="flex flex-col gap-1">
              <label class="text-xs font-medium text-ink-gray-6">
                {{ __("Reference") }}
              </label>
              <Link :doctype="form.refDoctype" v-model="form.refName" />
            </div>
          </template>

          <div class="flex flex-col gap-1">
            <label class="text-xs font-medium text-ink-gray-6">{{ __("Message") }}</label>
            <textarea
              v-model="form.message"
              rows="3"
              :placeholder="__('What do you want to be reminded about?')"
              class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
            />
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-xs font-medium text-ink-gray-6">{{ __("Remind at") }}</label>
            <input
              v-model="form.remindAt"
              type="datetime-local"
              class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            />
          </div>

          <label v-if="!editing" class="flex items-center gap-2 cursor-pointer select-none">
            <input
              v-model="form.sendEmail"
              type="checkbox"
              class="rounded border-outline-gray-2"
            />
            <span class="text-sm text-ink-gray-7 flex items-center gap-1">
              <LucideMail class="size-3.5 text-ink-gray-5" />
              {{ __("Also send me an email when due") }}
            </span>
          </label>
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          theme="blue"
          class="w-full"
          :loading="saving"
          :disabled="!form.message.trim() || !form.remindAt"
          @click="save"
        >
          {{ editing ? __("Reschedule") : __("Set reminder") }}
        </Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import {
  Badge,
  Button,
  Dialog,
  call,
  createResource,
  dayjs,
  toast,
  usePageMeta,
} from "frappe-ui";
import { RouterLink } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import LucideBell from "~icons/lucide/bell";
import LucideBellOff from "~icons/lucide/bell-off";
import LucideCheckCheck from "~icons/lucide/check-check";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideClock from "~icons/lucide/clock";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideX from "~icons/lucide/x";
import LucidePlus from "~icons/lucide/plus";
import LucideMail from "~icons/lucide/mail";
import LucideExternalLink from "~icons/lucide/external-link";

// ── Data ──────────────────────────────────────────────────────────────────────

const allRes = createResource({
  url: "helpdesk.api.reminder.get_all_my_reminders",
  auto: true,
});
const all = computed(() => (allRes.data as any[]) || []);

// ── Tabs ──────────────────────────────────────────────────────────────────────

const activeTab = ref("all");

const tabs = computed(() => [
  {
    key: "all",
    label: "All",
    badge: all.value.filter((r) => r.status !== "Dismissed").length,
  },
  {
    key: "overdue",
    label: "Overdue",
    badge: all.value.filter((r) => isDue(r)).length,
  },
  {
    key: "upcoming",
    label: "Upcoming",
    badge: all.value.filter((r) => r.status === "Pending" && !isDue(r)).length,
  },
  { key: "performed", label: "Performed", badge: 0 },
  { key: "dismissed", label: "Dismissed", badge: 0 },
]);

const filtered = computed(() => {
  switch (activeTab.value) {
    case "overdue":
      return all.value.filter((r) => isDue(r));
    case "upcoming":
      return all.value.filter((r) => r.status === "Pending" && !isDue(r));
    case "performed":
      return all.value.filter((r) => r.status === "Performed");
    case "dismissed":
      return all.value.filter((r) => r.status === "Dismissed");
    default:
      return all.value.filter((r) => r.status !== "Dismissed");
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function isDue(r: any): boolean {
  return (
    (r.status === "Pending" || r.status === "Notified") &&
    dayjs(r.remind_at).isBefore(dayjs())
  );
}

function iconFor(r: any) {
  if (r.status === "Performed") return LucideCheckCircle;
  if (isDue(r)) return LucideAlertCircle;
  return LucideClock;
}

function iconBg(r: any) {
  if (r.status === "Performed") return "bg-emerald-100 text-emerald-600";
  if (isDue(r)) return "bg-red-100 text-red-500";
  if (r.status === "Dismissed") return "bg-surface-gray-2 text-ink-gray-4";
  return "bg-violet-100 text-violet-600";
}

function statusTheme(status: string) {
  return (
    {
      Pending: "blue",
      Notified: "orange",
      Performed: "green",
      Dismissed: "gray",
    }[status] || "gray"
  );
}

function fmtTime(dt: string): string {
  const d = dayjs(dt);
  const now = dayjs();
  if (d.isBefore(now)) return d.format("MMM D, HH:mm") + " — overdue";
  if (d.isBefore(now.endOf("day"))) return __("Today") + " " + d.format("HH:mm");
  if (d.isBefore(now.add(1, "day").endOf("day")))
    return __("Tomorrow") + " " + d.format("HH:mm");
  return d.format("MMM D, YYYY HH:mm");
}

function refRoute(r: any) {
  const dt: string = r.reference_doctype || "";
  const name: string = r.reference_name || "";
  if (!dt || !name) return "/";
  const p = isCustomerPortal.value;
  if (dt === "HD Ticket")
    return {
      name: p ? "TicketCustomer" : "TicketAgent",
      params: { ticketId: name },
    };
  if (dt === "HD Project")
    return {
      name: p ? "ProjectCustomer" : "ProjectAgent",
      params: { projectId: name },
    };
  if (dt === "HD Addon")
    return {
      name: p ? "AddonCustomer" : "AddonAgent",
      params: { addonId: name },
    };
  return "/";
}

// ── Form ──────────────────────────────────────────────────────────────────────

const showForm = ref(false);
const editing = ref<any>(null);
const saving = ref(false);
const form = reactive({
  message: "",
  remindAt: "",
  refDoctype: "",
  refName: "",
  sendEmail: false,
});

function openCreate() {
  editing.value = null;
  const d = dayjs().add(1, "day").hour(9).minute(0).second(0);
  form.message = "";
  form.remindAt = d.format("YYYY-MM-DDTHH:mm");
  form.refDoctype = "";
  form.refName = "";
  form.sendEmail = false;
  showForm.value = true;
}

function openEdit(r: any) {
  editing.value = r;
  form.message = r.message;
  form.remindAt = dayjs(r.remind_at).format("YYYY-MM-DDTHH:mm");
  showForm.value = true;
}

async function save() {
  if (!form.message.trim() || !form.remindAt) return;
  saving.value = true;
  try {
    if (editing.value) {
      await call("helpdesk.api.reminder.update_reminder", {
        name: editing.value.name,
        message: form.message.trim(),
        remind_at: form.remindAt.replace("T", " ") + ":00",
      });
      toast.success(__("Rescheduled"));
    } else {
      await call("helpdesk.api.reminder.create_reminder", {
        message: form.message.trim(),
        remind_at: form.remindAt.replace("T", " ") + ":00",
        reference_doctype: form.refDoctype || null,
        reference_name: form.refName || null,
        send_email: form.sendEmail ? 1 : 0,
      });
      toast.success(__("Reminder set"));
    }
    showForm.value = false;
    allRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save"));
  } finally {
    saving.value = false;
  }
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function markDone(name: string) {
  try {
    await call("helpdesk.api.reminder.mark_performed", { name });
    allRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not update"));
  }
}

async function dismissReminder(name: string) {
  try {
    await call("helpdesk.api.reminder.dismiss_reminder", { name });
    allRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not dismiss"));
  }
}

usePageMeta(() => ({ title: __("Reminders") }));
</script>
