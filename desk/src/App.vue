<template>
  <FrappeUIProvider>
    <PortalRoot />
  </FrappeUIProvider>
  <Dialogs />
</template>

<script setup lang="ts">
import { Dialogs } from "@/components/dialogs";
import { useConfigStore } from "@/stores/config";
import { globalStore } from "@/stores/globalStore";
import { FrappeUIProvider, toast, setConfig, useTheme } from "frappe-ui";
import { computed, defineAsyncComponent, h, onMounted, onUnmounted } from "vue";
import Wifi from "~icons/lucide/wifi";
import WifiOff from "~icons/lucide/wifi-off";
import LucideListChecks from "~icons/lucide/list-checks";
import { useAuthStore } from "./stores/auth";
import { useFavicon } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { __ } from "./translation";
import { isCustomerPortal } from "./utils";

const configStore = useConfigStore();
const { favicon } = storeToRefs(configStore);

useFavicon(favicon);

if (!localStorage.getItem("theme")) {
  localStorage.setItem("theme", "light");
}
useTheme();

// In-app popup when a task is assigned to the current user (works even when
// email isn't configured). The server emits this to the assignee's user room.
function onTaskAssigned(data: {
  subject?: string;
  assigned_by?: string;
  context?: string;
}) {
  toast.create({
    title: __("New task assigned"),
    message: data?.assigned_by
      ? __("{0} assigned you “{1}”", [data.assigned_by, data.subject || ""])
      : data?.subject || __("A task was assigned to you"),
    icon: h(LucideListChecks, { class: "text-ink-white" }),
  });
}

// In-app popup when a task is ready for the current user's review.
function onTaskReviewRequested(data: { subject?: string }) {
  toast.create({
    title: __("Review requested"),
    message: __("“{0}” is ready for your review", [data?.subject || ""]),
    icon: h(LucideListChecks, { class: "text-ink-white" }),
  });
}

onMounted(() => {
  window.addEventListener("online", () => {
    toast.create({
      message: __("You are now online."),
      icon: h(Wifi, { class: "text-ink-white" }),
    });
  });

  window.addEventListener("offline", () => {
    toast.create({
      message: __("You are now offline."),
      icon: h(WifiOff, { class: "text-ink-white" }),
    });
  });
  !isCustomerPortal.value && setConfig("localTimezone", window.timezone?.user);
  setConfig("systemTimezone", window.timezone?.system || null);

  const { $socket } = globalStore();
  $socket?.on("helpdesk:task_assigned", onTaskAssigned);
  $socket?.on("helpdesk:task_review_requested", onTaskReviewRequested);
});

onUnmounted(() => {
  const { $socket } = globalStore();
  $socket?.off("helpdesk:task_assigned", onTaskAssigned);
  $socket?.off("helpdesk:task_review_requested", onTaskReviewRequested);
});

const AgentPortalRoot = defineAsyncComponent(
  () => import("@/pages/desk/AgentRoot.vue")
);
const CustomerPortalRoot = defineAsyncComponent(
  () => import("@/pages/CustomerPortalRoot.vue")
);

const PortalRoot = computed(() => {
  const authStore = useAuthStore();
  if (authStore.hasDeskAccess && authStore.isAgent) {
    return AgentPortalRoot;
  } else {
    return CustomerPortalRoot;
  }
});
</script>
