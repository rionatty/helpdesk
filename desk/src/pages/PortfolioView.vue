<template>
  <div class="flex flex-col h-full">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideLayoutGrid class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">{{ __("Portfolio") }}</div>
        </div>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-2xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-5 flex-1 overflow-y-auto"
    >
      <!-- Summary -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div
          v-for="c in summaryCards"
          :key="c.label"
          class="rounded-xl border border-outline-gray-1 bg-surface-white px-4 py-3 shadow-sm"
        >
          <div class="text-2xl font-bold leading-none" :class="c.color">
            {{ c.value }}
          </div>
          <div class="text-[11px] font-medium text-ink-gray-5 mt-1">{{ c.label }}</div>
        </div>
      </div>

      <!-- Projects -->
      <div class="executive-card overflow-hidden">
        <div
          class="grid grid-cols-12 gap-2 px-4 py-2.5 text-[11px] font-semibold text-ink-gray-5 uppercase tracking-wide border-b border-outline-gray-1"
        >
          <div class="col-span-4">{{ __("Project") }}</div>
          <div class="col-span-2">{{ __("Status") }}</div>
          <div class="col-span-2">{{ __("Progress") }}</div>
          <div class="col-span-2">{{ __("Tasks") }}</div>
          <div class="col-span-2">{{ __("Budget") }}</div>
        </div>
        <button
          v-for="p in projects"
          :key="p.name"
          type="button"
          class="grid grid-cols-12 gap-2 items-center px-4 py-3 w-full text-start border-b border-outline-gray-1 hover:bg-surface-menu-bar transition-colors"
          @click="open(p.name)"
        >
          <div class="col-span-4 min-w-0">
            <div class="flex items-center gap-1.5">
              <span
                v-if="p.at_risk"
                class="size-2 rounded-full bg-red-500 shrink-0"
                :title="__('At risk')"
              />
              <span class="text-sm font-medium text-ink-gray-8 truncate">
                {{ p.project_name }}
              </span>
            </div>
            <div class="text-xs text-ink-gray-5 truncate">
              {{ p.customer || __("Internal") }}
              <template v-if="p.lead_name"> · {{ p.lead_name }}</template>
            </div>
          </div>
          <div class="col-span-2">
            <Badge :label="p.status" :theme="statusTheme(p.status)" variant="subtle" />
          </div>
          <div class="col-span-2">
            <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500"
                :style="{ width: (p.progress || 0) + '%' }"
              />
            </div>
            <div class="text-[11px] text-ink-gray-5 mt-0.5">
              {{ p.milestones_done }}/{{ p.milestones_total }} {{ __("milestones") }}
            </div>
          </div>
          <div class="col-span-2 text-xs text-ink-gray-7">
            {{ p.tasks_done }}/{{ p.tasks_total }}
            <span v-if="p.tasks_overdue" class="text-red-600 font-medium">
              · {{ p.tasks_overdue }} {{ __("overdue") }}
            </span>
          </div>
          <div class="col-span-2">
            <template v-if="p.budget.budget_hours || p.budget.logged_hours">
              <div class="h-1.5 w-full rounded-full bg-surface-gray-3 overflow-hidden">
                <div
                  class="h-full rounded-full"
                  :class="p.budget.over_budget ? 'bg-red-500' : 'bg-emerald-500'"
                  :style="{ width: Math.min(p.budget.consumed_pct, 100) + '%' }"
                />
              </div>
              <div
                class="text-[11px] mt-0.5"
                :class="p.budget.over_budget ? 'text-red-600 font-medium' : 'text-ink-gray-5'"
              >
                {{ p.budget.logged_hours }}h<template v-if="p.budget.budget_hours">
                  / {{ p.budget.budget_hours }}h</template
                >
              </div>
            </template>
            <span v-else class="text-[11px] text-ink-gray-4">—</span>
          </div>
        </button>
        <div
          v-if="!projects.length && !resource.loading"
          class="px-4 py-10 text-center text-sm text-ink-gray-5"
        >
          {{ __("No projects to show.") }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Badge, createResource, usePageMeta } from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import { __ } from "@/translation";
import LucideLayoutGrid from "~icons/lucide/layout-grid";

const router = useRouter();

const resource = createResource({
  url: "helpdesk.api.project.get_portfolio",
  auto: true,
});
const projects = computed<any[]>(() => resource.data?.projects || []);
const summary = computed<any>(() => resource.data?.summary || {});

const summaryCards = computed(() => [
  { label: __("Projects"), value: summary.value.total || 0, color: "text-ink-gray-9" },
  { label: __("Active"), value: summary.value.active || 0, color: "text-blue-600" },
  { label: __("At risk"), value: summary.value.at_risk || 0, color: "text-red-600" },
  { label: __("Completed"), value: summary.value.completed || 0, color: "text-green-600" },
  {
    label: __("Logged / budget hrs"),
    value: `${summary.value.logged_hours || 0} / ${summary.value.budget_hours || 0}`,
    color: "text-emerald-600",
  },
]);

function statusTheme(status: string) {
  return (
    {
      Planned: "gray",
      Active: "blue",
      "On Hold": "orange",
      Completed: "green",
      Cancelled: "red",
    }[status] || "gray"
  );
}
function open(name: string) {
  router.push({ name: "ProjectAgent", params: { projectId: name } });
}

usePageMeta(() => ({ title: __("Portfolio") }));
</script>
