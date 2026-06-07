<template>
  <div
    class="p-4 md:p-5 md:pb-10 md:px-10 w-full overflow-scroll items-center relative bg-customer-portal"
  >
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideBookOpen class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Knowledge Base") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <RouterLink
          :to="{ name: 'TicketNew' }"
          class="inline-flex"
          :aria-label="__('Still need help? Open a new ticket')"
        >
          <Button variant="subtle" theme="blue">
            <template #prefix><LucideMessageCircle class="size-4" /></template>
            <span class="hidden md:inline">{{ __("Still need help?") }}</span>
          </Button>
        </RouterLink>
      </template>
    </LayoutHeader>
    <div
      class="max-w-4xl 2xl:max-w-5xl pt-2 sm:px-5 w-full flex flex-col gap-8 mx-auto"
    >
      <!-- Hero -->
      <section
        class="bg-customer-portal pt-6 flex flex-col items-center text-center gap-3 py-6 md:py-10 animate-in-fade"
      >
        <div
          class="max-w-2xl mx-auto bg-surface-white rounded-2xl shadow-sm border border-outline-gray-1 p-6 flex flex-col items-center gap-3 w-full"
        >
          <h1 class="executive-heading text-2xl md:text-3xl text-ink-gray-9">
            {{ __("How can we help?") }}
          </h1>
          <p class="text-base text-ink-gray-6 max-w-xl">
            {{
              __(
                "Search the knowledge base or browse by topic. Can't find what you need? Open a ticket and we'll help."
              )
            }}
          </p>
          <div class="w-full max-w-xl mt-2">
            <SearchPopover
              :popoverClass="[
                'max-w-[310px] md:max-w-[640px] !top-1 md:min-w-[640px]',
              ]"
              v-model="query"
              :placeholder="__('Search articles, e.g. \'reset password\'…')"
              size="md"
              :autofocus="true"
            />
          </div>
          <div class="flex items-center gap-1.5 text-sm text-ink-gray-5 mt-1">
            <LucideClock class="size-3.5" />
            <span>{{ __("We typically reply within a few hours.") }}</span>
          </div>
        </div>
      </section>

      <!-- Popular Articles -->
      <section
        v-if="popularArticles.data && popularArticles.data.length"
        class="flex flex-col gap-3"
      >
        <div class="flex items-center gap-2">
          <LucideFlame class="size-4 text-orange-500" />
          <p class="text-lg font-medium text-ink-gray-9">
            {{ __("Most viewed") }}
          </p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <RouterLink
            v-for="a in popularArticles.data"
            :key="a.name"
            class="flex flex-col gap-1 rounded-lg border border-outline-gray-2 hover:border-outline-gray-4 hover:shadow-sm px-4 py-3 transition-all"
            :to="{ name: 'ArticlePublic', params: { articleId: a.name } }"
          >
            <div class="font-medium text-ink-gray-8 truncate">
              {{ a.title }}
            </div>
            <div class="flex items-center gap-1.5 text-xs text-ink-gray-5">
              <LucideEye class="size-3.5" />
              <span>{{ a.views || 0 }} {{ __("views") }}</span>
            </div>
          </RouterLink>
        </div>
      </section>

      <!-- Categories Folder -->
      <section class="flex flex-col gap-3">
        <p class="text-lg font-medium text-ink-gray-9">
          {{ __("Browse by category") }}
        </p>
        <CategoryFolderContainer />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Button, createListResource, usePageMeta } from "frappe-ui";
import { RouterLink } from "vue-router";

import { LayoutHeader } from "@/components";
import CategoryFolderContainer from "@/components/knowledge-base/CategoryFolderContainer.vue";
import SearchPopover from "@/components/SearchPopover.vue";
import { capture } from "@/telemetry";
import { __ } from "@/translation";

const query = ref("");

const popularArticles = createListResource({
  doctype: "HD Article",
  fields: ["name", "title", "views", "category"],
  filters: { status: "Published" },
  orderBy: "views desc",
  pageLength: 6,
  auto: true,
});

onMounted(() => {
  capture("kb_customer_page_viewed");
});
usePageMeta(() => {
  return {
    title: "Knowledge Base",
  };
});
</script>
