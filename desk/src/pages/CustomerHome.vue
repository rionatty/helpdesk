<template>
  <div class="overflow-y-auto h-full bg-customer-portal flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideHome class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Home") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <Button
            variant="ghost"
            :aria-label="__('Search the knowledge base')"
            @click="router.push({ name: 'CustomerKnowledgeBase' })"
          >
            <template #prefix><LucideSearch class="size-4" /></template>
            <span class="hidden md:inline">{{ __("Search") }}</span>
          </Button>
          <Button
            variant="subtle"
            theme="blue"
            :aria-label="__('Get help — open a new ticket')"
            @click="router.push({ name: 'TicketNew' })"
          >
            <template #prefix><LucideHelpCircle class="size-4" /></template>
            <span class="hidden md:inline">{{ __("Get Help") }}</span>
          </Button>
        </div>
      </template>
    </LayoutHeader>
    <div
      class="w-full max-w-screen-2xl mx-auto px-4 md:px-6 lg:px-8 py-6 md:py-8 flex flex-col gap-6 md:gap-8 flex-1"
    >
      <!-- Greeting bar — navy + gold brand -->
      <section
        class="hd-brand-hero rounded-2xl px-6 py-5 md:px-8 mt-4 flex flex-col md:flex-row md:items-center justify-between gap-4 animate-in-fade"
      >
        <div class="flex items-center gap-3">
          <Avatar
            size="2xl"
            :label="authStore.userName"
            :image="authStore.userImage"
            class="ring-2 ring-offset-2 ring-[var(--hd-gold)]/40"
          />
          <div>
            <div class="executive-heading text-2xl text-white leading-tight">
              {{ greeting }}, {{ firstName }}
            </div>
            <div class="text-sm hd-on-navy-soft mt-1">
              {{ todayLabel }} · {{ brandName }}
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <div
            class="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/15 bg-white/10"
          >
            <div
              class="size-8 rounded-full bg-[var(--hd-gold)]/15 flex items-center justify-center"
            >
              <LucideTicket class="size-4 text-[var(--hd-gold)]" />
            </div>
            <div class="leading-tight">
              <div class="text-lg font-semibold text-white">
                {{ openTicketsCount }}
              </div>
              <div class="text-xs hd-on-navy-muted">{{ __("Open tickets") }}</div>
            </div>
          </div>
          <RouterLink
            :to="{ name: 'TicketNew' }"
            class="hd-gold-solid flex items-center gap-2 px-3 py-2 rounded-lg transition-colors"
          >
            <LucidePlus class="size-4" />
            <span>{{ __("New ticket") }}</span>
          </RouterLink>
        </div>
      </section>

      <!-- Customer dashboard stats -->
      <section class="px-4 md:px-8 mt-6">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div
            class="executive-card executive-card-hover hd-color-card group flex flex-col gap-3 px-5 py-5 pt-6"
            data-accent="blue"
          >
            <div
              class="size-12 rounded-2xl flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40 hd-icon-blue"
            >
              <LucideCheckCircle class="size-6 text-white" />
            </div>
            <div>
              <div class="text-2xl font-bold text-ink-gray-9">
                {{ openTicketsCount }}
              </div>
              <div class="text-sm font-medium text-ink-gray-8">
                {{ __("Open Tickets") }}
              </div>
              <div class="text-xs text-ink-gray-6">
                {{ __("Awaiting your attention") }}
              </div>
            </div>
          </div>
          <div
            class="executive-card executive-card-hover hd-color-card group flex flex-col gap-3 px-5 py-5 pt-6"
            data-accent="emerald"
          >
            <div
              class="size-12 rounded-2xl flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40 hd-icon-emerald"
            >
              <LucideCheckCheck class="size-6 text-white" />
            </div>
            <div>
              <div class="text-2xl font-bold text-ink-gray-9">
                {{ resolvedThisMonthCount }}
              </div>
              <div class="text-sm font-medium text-ink-gray-8">
                {{ __("Resolved This Month") }}
              </div>
              <div class="text-xs text-ink-gray-6">
                {{ __("Last 30 days") }}
              </div>
            </div>
          </div>
          <div
            class="executive-card executive-card-hover hd-color-card group flex flex-col gap-3 px-5 py-5 pt-6"
            data-accent="amber"
          >
            <div
              class="size-12 rounded-2xl flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40 hd-icon-amber"
            >
              <LucideTicket class="size-6 text-white" />
            </div>
            <div>
              <div class="text-2xl font-bold text-ink-gray-9">
                {{ totalTicketsCount }}
              </div>
              <div class="text-sm font-medium text-ink-gray-8">
                {{ __("Total Tickets") }}
              </div>
              <div class="text-xs text-ink-gray-6">
                {{ __("All-time count") }}
              </div>
            </div>
          </div>
          <div
            class="executive-card executive-card-hover hd-color-card group flex flex-col gap-3 px-5 py-5 pt-6"
            data-accent="rose"
          >
            <div class="flex items-center gap-3">
              <div
                class="size-12 rounded-2xl flex items-center justify-center shadow-md ring-1 ring-inset ring-white/40 hd-icon-rose"
              >
                <LucideHistory class="size-6 text-white" />
              </div>
              <div class="text-sm font-semibold text-ink-gray-8">
                {{ __("Recent Activity") }}
              </div>
            </div>
            <ul class="flex flex-col divide-y divide-outline-gray-1">
              <li
                v-for="t in recentTickets.data || []"
                :key="t.name"
                class="py-1.5"
              >
                <RouterLink
                  :to="`/my-tickets/${t.name}`"
                  class="flex items-center justify-between gap-2 hover:bg-surface-menu-bar rounded px-1 py-0.5"
                >
                  <span
                    class="truncate text-xs text-ink-gray-8 font-medium"
                  >#{{ t.name }} {{ t.subject || __("(no subject)") }}</span>
                  <span
                    v-if="t.status"
                    class="text-[10px] uppercase tracking-wide text-ink-gray-6 shrink-0"
                  >{{ t.status }}</span>
                </RouterLink>
              </li>
              <li
                v-if="recentTickets.loading"
                class="py-2 text-xs text-ink-gray-5"
              >
                {{ __("Loading…") }}
              </li>
              <li
                v-else-if="(recentTickets.data || []).length === 0"
                class="py-2 text-xs text-ink-gray-5"
              >
                {{ __("No recent tickets") }}
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Customer analytics charts -->
      <CustomerAnalytics />

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
            class="flex flex-col items-center justify-center gap-2 py-8 text-center"
          >
            <LucideInbox class="size-8 text-ink-gray-4" />
            <p class="text-sm text-ink-gray-5">
              {{ __("No published articles yet.") }}
            </p>
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
        class="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 pt-6 mt-2 border-t border-outline-gray-1"
      >
        <div
          v-for="t in trustBadges"
          :key="t.label"
          class="flex flex-col md:flex-row items-center md:items-start text-center md:text-start gap-2 md:gap-3"
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
import { ref, computed } from "vue";
import {
  Avatar,
  Button,
  createListResource,
  createResource,
  dayjs,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader } from "@/components";
import CustomerAnalytics from "@/components/CustomerAnalytics.vue";
import { useConfigStore } from "@/stores/config";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucideSearch from "~icons/lucide/search";
import LucideHeadphones from "~icons/lucide/headphones";
import LucideHome from "~icons/lucide/home";
import LucideHelpCircle from "~icons/lucide/help-circle";
import LucideInbox from "~icons/lucide/inbox";
import LucideChevronRight from "~icons/lucide/chevron-right";
import LucideFileText from "~icons/lucide/file-text";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideTicket from "~icons/lucide/ticket";
import LucidePlus from "~icons/lucide/plus";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideBell from "~icons/lucide/bell";
import LucideMail from "~icons/lucide/mail";
import LucideMessageCircle from "~icons/lucide/message-circle";
import LucideClock from "~icons/lucide/clock";
import LucideShield from "~icons/lucide/shield";
import LucideUsers from "~icons/lucide/users";
import LucideStar from "~icons/lucide/star";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideCheckCheck from "~icons/lucide/check-check";
import LucideHistory from "~icons/lucide/history";

const router = useRouter();
const config = useConfigStore();
const authStore = useAuthStore();
const searchQuery = ref("");

const firstName = computed(() => {
  const n = authStore.userName || "";
  return n.split(" ")[0] || n || __("there");
});
const greeting = computed(() => {
  const hour = dayjs().hour();
  if (hour < 5) return __("Hello");
  if (hour < 12) return __("Good morning");
  if (hour < 18) return __("Good afternoon");
  return __("Good evening");
});
const todayLabel = computed(() => dayjs().format("dddd, MMM D"));
const brandName = computed(() => config.brandName || __("Support"));

const popularArticles = createListResource({
  doctype: "HD Article",
  fields: ["name", "title", "views"],
  filters: { status: "Published" },
  orderBy: "views desc",
  pageLength: 5,
  auto: true,
});

const myEmail = computed(() => authStore.userId);

// Reliable integer counts via frappe.client.get_count (not list totalCount,
// which is unreliable in frappe-ui beta and underreports with pageLength:1).
const openTickets = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({
    doctype: "HD Ticket",
    filters: {
      raised_by: myEmail.value,
      status_category: ["!=", "Resolved"],
    },
  }),
  auto: true,
});
const totalTickets = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({
    doctype: "HD Ticket",
    filters: { raised_by: myEmail.value },
  }),
  auto: true,
});
const thirtyDaysAgo = computed(() => {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().split("T")[0];
});
const resolvedThisMonth = createResource({
  url: "frappe.client.get_count",
  makeParams: () => ({
    doctype: "HD Ticket",
    filters: {
      raised_by: myEmail.value,
      status_category: "Resolved",
      resolution_date: [">=", thirtyDaysAgo.value],
    },
  }),
  auto: true,
});
const recentTickets = createListResource({
  doctype: "HD Ticket",
  fields: ["name", "subject", "status", "modified"],
  filters: computed(() => ({ raised_by: myEmail.value })),
  orderBy: "modified desc",
  pageLength: 5,
  auto: true,
});
const openTicketsCount = computed(() => openTickets.data ?? 0);
const totalTicketsCount = computed(() => totalTickets.data ?? 0);
const resolvedThisMonthCount = computed(() => resolvedThisMonth.data ?? 0);

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
