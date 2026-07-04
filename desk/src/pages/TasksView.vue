<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideListChecks class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Tasks") }}
          </div>
        </div>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-4 flex-1 overflow-y-auto"
    >
      <div class="executive-card p-5">
        <TaskBoard hub :editable="true" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePageMeta } from "frappe-ui";
import { LayoutHeader } from "@/components";
import TaskBoard from "@/components/TaskBoard.vue";
import { __ } from "@/translation";
import LucideListChecks from "~icons/lucide/list-checks";

usePageMeta(() => ({
  title: __("Tasks"),
}));
</script>
