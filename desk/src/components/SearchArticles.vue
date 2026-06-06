<template>
  <div
    v-if="Boolean(articles.data?.length) && query.length > 2"
    class="rounded-lg border border-outline-blue-1 bg-surface-blue-1 p-4 text-base"
  >
    <div class="mb-3 flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 font-medium text-ink-gray-8">
        <LucideLightbulb class="size-4 text-blue-600" />
        <span>{{ __("Maybe one of these solves it?") }}</span>
      </div>
      <RouterLink
        v-if="!hideViewAll"
        class="text-xs text-ink-gray-6 hover:text-ink-gray-9 underline"
        :to="{ name: 'CustomerKnowledgeBase' }"
        target="_blank"
      >
        {{ __("Browse all articles") }}
      </RouterLink>
    </div>
    <dl class="mx-auto w-full flex flex-col gap-1.5">
      <RouterLink
        v-for="a in articles.data"
        :key="a.id"
        class="group flex flex-col gap-0.5 rounded-md bg-surface-white px-3 py-2 hover:bg-surface-blue-2 transition-colors"
        :to="{
          name: 'ArticlePublic',
          params: { articleId: a.name.split('#')[0] },
          hash: `#${a.name.split('#')[1]}`,
        }"
        @click="handleSearchArticleClick(a)"
        target="_blank"
      >
        <dt class="font-medium text-ink-gray-8 group-hover:text-ink-gray-9">
          {{ a.subject }}
          <span class="text-ink-gray-5 font-normal">— {{ a.headings }}</span>
        </dt>
        <dd
          class="text-p-sm text-ink-gray-6 line-clamp-1"
          v-html="a.description"
        />
      </RouterLink>
    </dl>
    <div class="mt-3 text-xs text-ink-gray-5">
      {{ __("Don't see your answer? Keep going below to send your ticket.") }}
    </div>
  </div>
  <div
    v-else-if="
      !articles.loading && articles.data?.length === 0 && query.length > 2
    "
    class="flex items-center gap-3 rounded-lg border border-outline-gray-2 px-4 py-3 text-base"
  >
    <LucideSearch class="size-5 text-ink-gray-4 shrink-0" />
    <div class="flex flex-col">
      <p class="font-medium text-ink-gray-7">
        {{ __("No matching articles") }}
      </p>
      <span class="text-p-sm text-ink-gray-5">
        {{ __("Add a description below and we'll take it from here.") }}
      </span>
    </div>
  </div>
  <div
    v-else-if="articles.loading"
    class="flex items-center gap-3 rounded-lg border border-outline-gray-2 px-4 py-3 text-base"
  >
    <LucideSearch class="size-5 text-ink-gray-4 shrink-0 animate-pulse" />
    <div class="flex flex-col">
      <p class="font-medium text-ink-gray-7">
        {{ __("Looking for answers…") }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { capture } from "@/telemetry";
import { __ } from "@/translation";
import { createResource } from "frappe-ui";
import { watch } from "vue";
interface P {
  query: string;
  hideViewAll?: boolean;
}

const { query = "", hideViewAll = false } = defineProps<P>();
const articles = createResource({
  url: "helpdesk.api.article.search",
  debounce: 500,
  auto: false,
});
watch(
  () => query,
  (query) => {
    if (query.length < 3) return;
    articles.update({
      params: {
        query: query,
      },
    });
    articles.reload();
  }
);

function handleSearchArticleClick(article) {
  capture("kb_customer_search_article_clicked", {
    data: {
      article: article.subject,
    },
  });
}
</script>
