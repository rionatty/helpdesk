<template>
  <div class="flex h-12 items-center border-b border-outline-gray-1 hd-chrome-bg pe-5 rtl:pe-6 shadow-sm">
    <div id="app-header" class="flex-1 w-full"></div>
    <div class="flex items-center gap-1">
      <RemindersPopover />
      <CallUI :userEmail="user" />
    </div>
  </div>

  <!-- New-ticket popup (bottom-right, persistent across all pages) -->
  <Teleport to="body">
    <Transition name="slide-up">
      <div
        v-if="newTicketNotif"
        class="fixed bottom-5 right-5 z-[9999] w-80 rounded-xl border border-outline-gray-1 bg-surface-white shadow-2xl overflow-hidden"
      >
        <div class="flex items-center justify-between px-4 py-2.5 bg-blue-600">
          <div class="flex items-center gap-2">
            <LucideTicket class="size-3.5 text-white" />
            <span class="text-xs font-semibold text-white">{{ __("New Ticket") }}</span>
          </div>
          <button
            class="size-5 rounded flex items-center justify-center text-white/70 hover:text-white transition-colors"
            @click="closeNotif"
          >
            <LucideX class="size-3.5" />
          </button>
        </div>
        <div class="px-4 py-3">
          <p v-if="newTicketNotif.ticket_id" class="text-[11px] text-blue-600 font-mono font-semibold">
            #{{ newTicketNotif.ticket_id }}
          </p>
          <p class="text-sm font-medium text-ink-gray-9 mt-0.5 leading-snug">
            {{ newTicketNotif.subject || __("A new support ticket has been submitted.") }}
          </p>
          <p v-if="newTicketNotif.customer" class="text-xs text-ink-gray-5 mt-1">
            {{ __("From") }}: {{ newTicketNotif.customer }}
          </p>
          <div class="flex gap-2 mt-3">
            <button
              class="flex-1 text-xs font-medium py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              @click="viewTicket"
            >
              {{ __("View ticket") }}
            </button>
            <button
              class="flex-1 text-xs font-medium py-1.5 rounded-lg bg-surface-gray-2 text-ink-gray-7 hover:bg-surface-gray-3 transition-colors"
              @click="closeNotif"
            >
              {{ __("Dismiss") }}
            </button>
          </div>
        </div>
        <!-- Auto-dismiss progress bar -->
        <div class="h-0.5 bg-surface-gray-2">
          <div
            class="h-full bg-blue-400 transition-all ease-linear"
            :style="{ width: notifProgress + '%', transitionDuration: '1s' }"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import CallUI from "@/components/telephony/CallUI.vue";
import RemindersPopover from "@/components/RemindersPopover.vue";
import { useAuthStore } from "@/stores/auth";
import { useTelephonyStore } from "@/stores/telephony";
import { globalStore } from "@/stores/globalStore";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import LucideTicket from "~icons/lucide/ticket";
import LucideX from "~icons/lucide/x";

const { user } = useAuthStore();
const telephonyStore = useTelephonyStore();
const router = useRouter();
const { $socket } = globalStore();

// ── New-ticket notification popup ─────────────────────────────────────────────

const newTicketNotif = ref(null);
const notifProgress = ref(100);
let notifTimer = null;
let progressTimer = null;

function onNewTicket(data) {
  if (isCustomerPortal.value) return;
  newTicketNotif.value = data || {};
  notifProgress.value = 100;
  if (notifTimer) clearTimeout(notifTimer);
  if (progressTimer) clearInterval(progressTimer);

  let elapsed = 0;
  progressTimer = setInterval(() => {
    elapsed += 1;
    notifProgress.value = Math.max(0, 100 - (elapsed / 10) * 100);
  }, 1000);
  notifTimer = setTimeout(() => closeNotif(), 10_000);
}

function closeNotif() {
  newTicketNotif.value = null;
  if (notifTimer) { clearTimeout(notifTimer); notifTimer = null; }
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
}

function viewTicket() {
  if (newTicketNotif.value?.ticket_id) {
    router.push({ name: "TicketAgent", params: { ticketId: newTicketNotif.value.ticket_id } });
  } else {
    router.push({ name: "TicketsAgent" });
  }
  closeNotif();
}

onMounted(() => {
  telephonyStore.fetchCallIntegrationStatus();
  if (!isCustomerPortal.value) {
    $socket.on("helpdesk:new-ticket", onNewTicket);
  }
});

onUnmounted(() => {
  if (!isCustomerPortal.value) {
    $socket.off("helpdesk:new-ticket", onNewTicket);
  }
  if (notifTimer) clearTimeout(notifTimer);
  if (progressTimer) clearInterval(progressTimer);
});
</script>

<style scoped>
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
