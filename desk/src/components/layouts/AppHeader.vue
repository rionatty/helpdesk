<template>
  <div class="flex h-12 items-center border-b border-outline-gray-1 hd-chrome-bg pe-5 rtl:pe-6 shadow-sm">
    <div id="app-header" class="flex-1 w-full"></div>
    <div class="flex items-center gap-1">
      <RemindersPopover />
      <CallUI :userEmail="user" />
    </div>
  </div>
</template>

<script setup>
import CallUI from "@/components/telephony/CallUI.vue";
import RemindersPopover from "@/components/RemindersPopover.vue";
import { useAuthStore } from "@/stores/auth";
import { useTelephonyStore } from "@/stores/telephony";
import { onMounted } from "vue";

const { user } = useAuthStore();

const telephonyStore = useTelephonyStore();

onMounted(() => {
  telephonyStore.fetchCallIntegrationStatus();
});
</script>
