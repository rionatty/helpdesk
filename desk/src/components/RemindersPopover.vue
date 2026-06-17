<template>
  <div class="relative" ref="containerRef">
    <!-- Bell button -->
    <button
      class="relative flex items-center justify-center size-8 rounded-lg text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8 transition-colors"
      :title="__('Reminders')"
      @click="toggle"
    >
      <LucideBell class="size-4" />
      <span
        v-if="dueCount"
        class="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-0.5 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center"
      >
        {{ dueCount > 9 ? "9+" : dueCount }}
      </span>
    </button>

    <!-- Dropdown panel -->
    <Transition name="pop">
      <div
        v-if="isOpen"
        class="absolute right-0 top-10 z-50 w-80 rounded-xl border border-outline-gray-1 bg-surface-white shadow-xl overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-outline-gray-1 bg-surface-gray-1">
          <div class="flex items-center gap-2">
            <LucideBell class="size-4 text-ink-gray-6" />
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Reminders") }}
            </span>
            <span v-if="reminders.length" class="text-xs text-ink-gray-5">
              ({{ reminders.length }})
            </span>
          </div>
          <button
            class="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
            @click="showForm = !showForm"
          >
            <LucidePlus class="size-3.5" />
            {{ __("New") }}
          </button>
        </div>

        <!-- Inline new-reminder form -->
        <div v-if="showForm" class="px-4 py-3 border-b border-outline-gray-1 bg-blue-50/60 flex flex-col gap-2">
          <textarea
            v-model="newMsg"
            rows="2"
            :placeholder="__('Reminder message…')"
            class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
          />
          <input
            v-model="newAt"
            type="datetime-local"
            class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          />
          <div class="flex gap-2 justify-end">
            <button
              class="text-xs text-ink-gray-5 hover:text-ink-gray-8 px-2 py-1"
              @click="showForm = false"
            >
              {{ __("Cancel") }}
            </button>
            <button
              :disabled="!newMsg.trim() || !newAt || savingNew"
              class="text-xs font-medium px-3 py-1 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
              @click="saveNew"
            >
              {{ savingNew ? __("Saving…") : __("Set") }}
            </button>
          </div>
        </div>

        <!-- Reminder list -->
        <div class="max-h-72 overflow-y-auto">
          <div
            v-if="remindersRes.loading"
            class="py-6 text-sm text-center text-ink-gray-5"
          >
            {{ __("Loading…") }}
          </div>
          <div
            v-else-if="!reminders.length"
            class="py-8 flex flex-col items-center gap-2 text-ink-gray-5"
          >
            <LucideBellOff class="size-6 text-ink-gray-4" />
            <p class="text-sm">{{ __("No pending reminders") }}</p>
          </div>
          <div
            v-for="r in reminders"
            :key="r.name"
            class="flex items-start gap-3 px-4 py-3 border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1 transition-colors"
          >
            <!-- Icon -->
            <div
              class="mt-0.5 size-7 rounded-full shrink-0 flex items-center justify-center"
              :class="isDue(r.remind_at) ? 'bg-red-100 text-red-500' : 'bg-violet-100 text-violet-600'"
            >
              <LucideBell class="size-3.5" />
            </div>
            <!-- Content -->
            <div class="flex-1 min-w-0">
              <p class="text-sm text-ink-gray-8 leading-snug break-words">
                {{ r.message }}
              </p>
              <p
                class="text-xs mt-0.5"
                :class="isDue(r.remind_at) ? 'text-red-500 font-medium' : 'text-ink-gray-5'"
              >
                {{ formatTime(r.remind_at) }}
              </p>
              <RouterLink
                v-if="r.reference_name"
                :to="referenceRoute(r)"
                class="text-xs text-blue-600 hover:underline truncate block"
                @click="isOpen = false"
              >
                {{ r.reference_name }}
              </RouterLink>
            </div>
            <!-- Actions: mark done + dismiss -->
            <div class="flex items-center gap-0.5 shrink-0 mt-0.5">
              <button
                class="size-6 rounded flex items-center justify-center text-ink-gray-4 hover:bg-emerald-50 hover:text-emerald-600 transition-colors"
                :title="__('Mark as done')"
                @click.stop="markDone(r.name)"
              >
                <LucideCheckCheck class="size-3.5" />
              </button>
              <button
                class="size-6 rounded flex items-center justify-center text-ink-gray-4 hover:bg-surface-gray-3 hover:text-red-500 transition-colors"
                :title="__('Dismiss')"
                @click.stop="dismiss(r.name)"
              >
                <LucideX class="size-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>

  <!-- Realtime popup (bottom-right) -->
  <Teleport to="body">
    <Transition name="slide-up">
      <div
        v-if="realtimePopup"
        class="fixed bottom-5 right-5 z-[9999] w-80 rounded-xl border border-outline-gray-1 bg-surface-white shadow-2xl overflow-hidden"
      >
        <div class="flex items-center justify-between px-4 py-2.5 bg-violet-600">
          <div class="flex items-center gap-2">
            <LucideBell class="size-3.5 text-white" />
            <span class="text-xs font-semibold text-white">{{ __("Reminder") }}</span>
          </div>
          <button
            class="size-5 rounded flex items-center justify-center text-white/70 hover:text-white transition-colors"
            @click="closePopup"
          >
            <LucideX class="size-3.5" />
          </button>
        </div>
        <div class="px-4 py-3">
          <p class="text-sm text-ink-gray-9 font-medium leading-snug">
            {{ realtimePopup.message }}
          </p>
          <RouterLink
            v-if="realtimePopup.reference_name"
            :to="referenceRoute(realtimePopup)"
            class="text-xs text-blue-600 hover:underline mt-1 block"
            @click="closePopup"
          >
            {{ realtimePopup.reference_doctype }} · {{ realtimePopup.reference_name }}
          </RouterLink>
          <div class="flex gap-2 mt-3">
            <button
              class="flex-1 text-xs font-medium py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors flex items-center justify-center gap-1"
              @click="popupMarkDone"
            >
              <LucideCheckCheck class="size-3.5" />
              {{ __("Mark done") }}
            </button>
            <button
              class="flex-1 text-xs font-medium py-1.5 rounded-lg bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3 transition-colors"
              @click="popupDismiss"
            >
              {{ __("Dismiss") }}
            </button>
          </div>
        </div>
        <!-- Progress bar for auto-dismiss -->
        <div class="h-0.5 bg-surface-gray-2">
          <div
            class="h-full bg-violet-400 transition-all ease-linear"
            :style="{ width: popupProgress + '%', transitionDuration: '1s' }"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { call, createResource, dayjs, toast } from "frappe-ui";
import { globalStore } from "@/stores/globalStore";
import { __ } from "@/translation";
import LucideBell from "~icons/lucide/bell";
import LucideBellOff from "~icons/lucide/bell-off";
import LucideCheckCheck from "~icons/lucide/check-check";
import LucidePlus from "~icons/lucide/plus";
import LucideX from "~icons/lucide/x";

const { $socket } = globalStore();

const isOpen = ref(false);
const showForm = ref(false);
const newMsg = ref("");
const newAt = ref("");
const savingNew = ref(false);
const containerRef = ref<HTMLElement | null>(null);

// ── Reminder list ─────────────────────────────────────────────────────────────

const remindersRes = createResource({
  url: "helpdesk.api.reminder.get_my_reminders",
  auto: true,
});
const reminders = computed(() => (remindersRes.data as any[]) || []);
const dueCount = computed(
  () => reminders.value.filter((r) => isDue(r.remind_at)).length
);

function toggle() {
  isOpen.value = !isOpen.value;
  if (isOpen.value) remindersRes.reload();
}

function isDue(dt: string): boolean {
  return dayjs(dt).isBefore(dayjs());
}

function formatTime(dt: string): string {
  const d = dayjs(dt);
  const now = dayjs();
  if (d.isBefore(now)) return d.format("MMM D, HH:mm") + " — overdue";
  if (d.isBefore(now.endOf("day"))) return "Today " + d.format("HH:mm");
  if (d.isBefore(now.add(1, "day").endOf("day"))) return "Tomorrow " + d.format("HH:mm");
  return d.format("MMM D, HH:mm");
}

function referenceRoute(r: any): any {
  const dt: string = r.reference_doctype || "";
  const name: string = r.reference_name || "";
  if (!dt || !name) return "/";
  if (dt === "HD Ticket") return { name: "TicketAgent", params: { ticketId: name } };
  if (dt === "HD Project") return { name: "ProjectAgent", params: { projectId: name } };
  if (dt === "HD Addon") return { name: "AddonAgent", params: { addonId: name } };
  return "/";
}

// ── Actions ───────────────────────────────────────────────────────────────────

async function saveNew() {
  if (!newMsg.value.trim() || !newAt.value) return;
  savingNew.value = true;
  try {
    await call("helpdesk.api.reminder.create_reminder", {
      message: newMsg.value.trim(),
      remind_at: newAt.value.replace("T", " ") + ":00",
    });
    toast.success(__("Reminder set"));
    newMsg.value = "";
    newAt.value = "";
    showForm.value = false;
    remindersRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not set reminder"));
  } finally {
    savingNew.value = false;
  }
}

async function markDone(name: string) {
  try {
    await call("helpdesk.api.reminder.mark_performed", { name });
    remindersRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not update"));
  }
}

async function dismiss(name: string) {
  try {
    await call("helpdesk.api.reminder.dismiss_reminder", { name });
    remindersRes.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not dismiss"));
  }
}

// ── Realtime popup ────────────────────────────────────────────────────────────

const realtimePopup = ref<any>(null);
const popupProgress = ref(100);
let popupTimer: ReturnType<typeof setTimeout> | null = null;
let progressTimer: ReturnType<typeof setInterval> | null = null;

function onReminderDue(data: any) {
  // Show the popup
  realtimePopup.value = data;
  remindersRes.reload();

  // Auto-dismiss after 30 s
  popupProgress.value = 100;
  if (popupTimer) clearTimeout(popupTimer);
  if (progressTimer) clearInterval(progressTimer);

  let elapsed = 0;
  progressTimer = setInterval(() => {
    elapsed += 1;
    popupProgress.value = Math.max(0, 100 - (elapsed / 30) * 100);
  }, 1000);

  popupTimer = setTimeout(() => {
    closePopup();
  }, 30_000);
}

function closePopup() {
  realtimePopup.value = null;
  if (popupTimer) { clearTimeout(popupTimer); popupTimer = null; }
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
}

async function popupMarkDone() {
  if (!realtimePopup.value) return;
  try {
    await call("helpdesk.api.reminder.mark_performed", { name: realtimePopup.value.name });
    remindersRes.reload();
  } catch {}
  closePopup();
}

async function popupDismiss() {
  if (!realtimePopup.value) return;
  try {
    await call("helpdesk.api.reminder.dismiss_reminder", { name: realtimePopup.value.name });
    remindersRes.reload();
  } catch {}
  closePopup();
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

function onClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    isOpen.value = false;
  }
}

let poll: ReturnType<typeof setInterval>;
onMounted(() => {
  document.addEventListener("mousedown", onClickOutside);
  poll = setInterval(() => remindersRes.reload(), 120_000);
  $socket.on("helpdesk:reminder_due", onReminderDue);
});
onUnmounted(() => {
  document.removeEventListener("mousedown", onClickOutside);
  clearInterval(poll);
  $socket.off("helpdesk:reminder_due", onReminderDue);
  if (popupTimer) clearTimeout(popupTimer);
  if (progressTimer) clearInterval(progressTimer);
});
</script>

<style scoped>
.pop-enter-active,
.pop-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(16px);
}
</style>
