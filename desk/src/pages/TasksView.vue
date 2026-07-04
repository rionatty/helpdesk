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
      <div
        class="flex items-start gap-2.5 rounded-xl border border-outline-blue-1 bg-surface-blue-1 px-4 py-3"
      >
        <LucideInfo class="size-4 text-blue-600 mt-0.5 shrink-0" />
        <p class="text-sm text-ink-gray-7">
          {{
            __(
              "Everything on your plate — tasks you created, are assigned to, or review, across projects and add-ons. Managers and admins see all. Use “Add a task” for personal to-dos; they're assigned to you by default."
            )
          }}
        </p>
      </div>
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
import LucideInfo from "~icons/lucide/info";

usePageMeta(() => ({
  title: __("Tasks"),
}));
</script>
