<template>
  <div class="overflow-y-auto h-full bg-customer-portal flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg font-medium text-ink-gray-9">
          {{ __("Home") }}
        </div>
      </template>
    </LayoutHeader>
    <div
      class="w-full max-w-[1280px] mx-auto px-4 md:px-8 lg:px-12 py-6 md:py-10 flex flex-col gap-8 flex-1"
    >
      <!-- Hero — navy + gold brand -->
      <section
        class="hd-brand-hero rounded-3xl p-6 md:px-10 md:py-9 flex flex-col md:flex-row items-center gap-6 md:gap-10 animate-in-fade"
      >
        <div class="flex-1 flex flex-col gap-4 max-w-xl">
          <h1
            class="executive-heading text-3xl md:text-[2.5rem] text-white leading-[1.1]"
          >
            {{ __("Hi there! How can we help you?") }}
          </h1>
          <p class="text-lg hd-on-navy-soft leading-relaxed">
            {{
              __(
                "Find answers, solve problems, and get the support you need."
              )
            }}
          </p>
          <form
            class="flex items-stretch gap-2 rounded-2xl bg-white shadow-md overflow-hidden mt-2 focus-within:ring-2 focus-within:ring-[var(--hd-gold)] transition-all"
            @submit.prevent="onSearch"
          >
            <div class="flex items-center px-3 text-ink-gray-5">
              <LucideSearch class="size-4" />
            </div>
            <input
              v-model="searchQuery"
              type="search"
              :placeholder="__('Search for articles, topics, or keywords…')"
              class="flex-1 bg-transparent outline-none text-base text-ink-gray-9 placeholder:text-ink-gray-4 py-3"
            />
            <button
              type="submit"
              class="hd-gold-solid px-5 transition-colors"
            >
              {{ __("Search") }}
            </button>
          </form>
          <div class="flex flex-wrap gap-2 mt-2">
            <span class="hd-pill hd-pill-gold">{{ __("Secure") }}</span>
            <span class="hd-pill hd-pill-emerald">{{ __("Fast") }}</span>
            <span class="hd-pill hd-pill-coral">{{ __("Official") }}</span>
          </div>
        </div>
        <div class="hidden md:flex shrink-0 items-center justify-center">
          <div
            class="size-44 lg:size-52 rounded-[2rem] bg-gradient-to-br from-white/15 to-white/5 border border-white/15 flex items-center justify-center shadow-2xl"
          >
            <LucideHeadphones class="size-20 lg:size-24 text-[var(--hd-gold)]" />
          </div>
        </div>
      </section>

      <!-- 4 action cards -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <RouterLink
          v-for="card in actionCards"
          :key="card.label"
          :to="card.to"
          :data-accent="card.accent"
          class="executive-card executive-card-hover hd-color-card group flex flex-col gap-4 px-5 py-5 pt-6"
        >
          <div
            class="size-12 rounded-2xl flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40"
            :class="card.iconBg"
          >
            <component :is="card.icon" class="size-6 text-white" />
          </div>
          <div>
            <div class="text-base font-semibold text-ink-gray-9">
              {{ __(card.label) }}
            </div>
            <p class="text-sm text-ink-gray-6 mt-1 leading-snug">
              {{ __(card.description) }}
            </p>
          </div>
          <div
            class="text-sm font-medium mt-auto flex items-center gap-1 group-hover:gap-2 transition-all"
            :class="card.ctaColor"
          >
            {{ __(card.cta) }}
            <LucideChevronRight class="size-4" />
          </div>
        </RouterLink>
      </section>

      <!-- Popular Articles + Need more help -->
      <section class="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <!-- Popular articles -->
        <div class="executive-card lg:col-span-3 p-6 flex flex-col gap-3">
          <div class="executive-heading text-lg text-ink-gray-9">
            {{ __("Popular Articles") }}
          </div>
          <div v-if="popularArticles.loading" class="text-sm text-ink-gray-5">
            {{ __("Loading…") }}
          </div>
          <div
            v-else-if="!popularArticles.data?.length"
            class="text-sm text-ink-gray-5"
          >
            {{ __("No published articles yet.") }}
          </div>
          <RouterLink
            v-for="a in popularArticles.data"
            :key="a.name"
            :to="{ name: 'ArticlePublic', params: { articleId: a.name } }"
            class="flex items-center justify-between gap-3 px-2 py-2.5 rounded-md hover:bg-surface-menu-bar transition-colors group"
          >
            <div class="flex items-center gap-2 min-w-0">
              <LucideFileText class="size-4 text-ink-gray-5 shrink-0" />
              <span class="text-sm text-ink-gray-8 truncate">{{ a.title }}</span>
            </div>
            <LucideChevronRight
              class="size-4 text-ink-gray-4 group-hover:text-ink-gray-7 transition-colors"
            />
          </RouterLink>
          <RouterLink
            v-if="popularArticles.data?.length"
            :to="{ name: 'CustomerKnowledgeBase' }"
            class="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1 mt-1 px-2"
          >
            {{ __("View all articles") }}
            <LucideChevronRight class="size-4" />
          </RouterLink>
        </div>

        <!-- Need more help -->
        <div class="executive-card lg:col-span-2 p-6 flex flex-col gap-3">
          <div>
            <div class="executive-heading text-lg text-ink-gray-9">
              {{ __("Need more help?") }}
            </div>
            <p class="text-sm text-ink-gray-6 mt-0.5">
              {{
                __(
                  "We're here for you. Choose the best way to reach us."
                )
              }}
            </p>
          </div>
          <div class="grid grid-cols-1 gap-2 mt-1">
            <button
              v-for="opt in helpOptions"
              :key="opt.label"
              type="button"
              class="flex items-center gap-3 rounded-xl border border-outline-gray-1 px-3 py-3 text-start hover:border-blue-300 hover:bg-blue-50/40 hover:shadow-sm transition-all"
              @click="opt.onClick"
            >
              <div
                class="size-10 rounded-full flex items-center justify-center shrink-0 shadow-sm ring-1 ring-inset ring-white/40"
                :class="opt.iconBg"
              >
                <component :is="opt.icon" class="size-5 text-white" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-ink-gray-8">
                  {{ __(opt.label) }}
                </div>
                <div class="text-xs text-ink-gray-5 truncate">
                  {{ __(opt.description) }}
                </div>
              </div>
              <LucideChevronRight class="size-4 text-ink-gray-4 shrink-0" />
            </button>
          </div>
        </div>
      </section>

      <!-- Trust badges -->
      <section
        class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2 pt-6 border-t border-outline-gray-1"
      >
        <div
          v-for="t in trustBadges"
          :key="t.label"
          class="flex items-start gap-3"
        >
          <div
            class="size-10 rounded-full flex items-center justify-center shrink-0 shadow-sm ring-1 ring-inset ring-white/40"
            :class="t.iconBg"
          >
            <component :is="t.icon" class="size-5 text-white" />
          </div>
          <div>
            <div class="text-sm font-semibold text-ink-gray-8">
              {{ __(t.label) }}
            </div>
            <div class="text-xs text-ink-gray-6 mt-0.5">
              {{ __(t.description) }}
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { createListResource, usePageMeta } from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";
import LucideSearch from "~icons/lucide/search";
import LucideHeadphones from "~icons/lucide/headphones";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideFileText from "~icons/lucide/file-text";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideTicket from "~icons/lucide/ticket";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideBell from "~icons/lucide/bell";
import LucideMail from "~icons/lucide/mail";
import LucideMessageCircle from "~icons/lucide/message-circle";
import LucideClock from "~icons/lucide/clock";
import LucideShield from "~icons/lucide/shield";
import LucideUsers from "~icons/lucide/users";
import LucideStar from "~icons/lucide/star";

const router = useRouter();
const config = useConfigStore();
const searchQuery = ref("");

const popularArticles = createListResource({
  doctype: "HD Article",
  fields: ["name", "title", "views"],
  filters: { status: "Published" },
  orderBy: "views desc",
  pageLength: 5,
  auto: true,
});

function onSearch() {
  router.push({
    name: "CustomerKnowledgeBase",
    query: searchQuery.value ? { q: searchQuery.value } : undefined,
  });
}

const actionCards = [
  {
    label: "Knowledge Base",
    description: "Browse articles and guides to find answers to common questions.",
    icon: LucideBookOpen,
    iconBg: "hd-icon-blue",
    ctaColor: "text-blue-600",
    accent: "blue",
    cta: "Explore articles",
    to: { name: "CustomerKnowledgeBase" },
  },
  {
    label: "Submit a Ticket",
    description: "Can't find what you need? Submit a ticket and our team will help you.",
    icon: LucideTicket,
    iconBg: "hd-icon-emerald",
    ctaColor: "text-emerald-600",
    accent: "emerald",
    cta: "Submit a ticket",
    to: { name: "TicketNew" },
  },
  {
    label: "My Tickets",
    description: "View your previous tickets, check status, and continue conversations.",
    icon: LucideListChecks,
    iconBg: "hd-icon-violet",
    ctaColor: "text-violet-600",
    accent: "violet",
    cta: "View my tickets",
    to: { name: "TicketsCustomer" },
  },
  {
    label: "System Status",
    description: "Check the status of our services and see any ongoing incidents.",
    icon: LucideBell,
    iconBg: "hd-icon-amber",
    ctaColor: "text-amber-600",
    accent: "amber",
    cta: "Check status",
    to: { name: "StatusPage" },
  },
];

const helpOptions = [
  {
    label: "Submit a ticket",
    description: "Open a ticket and our team will reply soon.",
    icon: LucideMessageCircle,
    iconBg: "hd-icon-indigo",
    onClick: () => router.push({ name: "TicketNew" }),
  },
  {
    label: "Email support",
    description: "Send us an email and we'll get back to you.",
    icon: LucideMail,
    iconBg: "hd-icon-rose",
    onClick: () => {
      window.location.href = `mailto:support@example.com?subject=${encodeURIComponent(
        "Help request"
      )}`;
    },
  },
  {
    label: "Business hours",
    description: "Mon–Fri, 9:00 AM – 6:00 PM (your local time).",
    icon: LucideClock,
    iconBg: "hd-icon-emerald",
    onClick: () => router.push({ name: "StatusPage" }),
  },
];

const trustBadges = [
  {
    label: "Secure & Confidential",
    description: "Your privacy and data are always protected.",
    icon: LucideShield,
    iconBg: "hd-icon-emerald",
  },
  {
    label: "Expert Support",
    description: "Our team is here to help you succeed.",
    icon: LucideUsers,
    iconBg: "hd-icon-indigo",
  },
  {
    label: "Customer First",
    description: "We're committed to providing the best support.",
    icon: LucideStar,
    iconBg: "hd-icon-amber",
  },
];

usePageMeta(() => ({
  title: `${config.brandName || __("Support")} — ${__("Home")}`,
}));
</script>
