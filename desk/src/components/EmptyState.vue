<template>
  <div
    v-if="variant === 'badge'"
    class="flex flex-col items-center justify-center gap-4 absolute inset-x-0 top-5.5 bottom-0 pointer-events-none"
  >
    <div
      class="p-4 size-14.5 rounded-full bg-surface-gray-1 flex justify-center items-center"
    >
      <component v-if="icon" :is="icon" class="size-6 text-ink-gray-6" />
    </div>
    <div class="flex flex-col items-center gap-1">
      <div class="text-base font-medium text-ink-gray-6">
        {{ __(title) }}
      </div>
      <div
        v-if="descriptionText"
        class="text-p-sm text-ink-gray-5 max-w-60 text-center"
      >
        {{ __(descriptionText) }}
      </div>
    </div>
  </div>
  <div
    v-else
    class="flex h-full items-center justify-center absolute inset-x-0 top-0 pointer-events-none animate-in-soft"
  >
    <div
      class="flex flex-col items-center gap-3 text-xl font-medium text-ink-gray-4 w-9/12 md:w-4/12"
    >
      <!-- overlay variant (for charts) -->
      <div
        v-if="variant === 'overlay'"
        class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none -z-10"
        :style="{
          backgroundImage:
            'radial-gradient(ellipse at center, var(--surface-white) 10%, color-mix(in srgb, var(--surface-white) 90%, transparent) 25%, transparent 70%)',
        }"
      />
      <!-- Icon in vibrant gradient circle — gives empty states a touch of brand -->
      <div
        v-if="icon"
        class="flex items-center justify-center size-14 rounded-full bg-gradient-to-br from-blue-100 via-violet-100 to-amber-100 ring-1 ring-inset ring-white/60 shadow-sm"
      >
        <component :is="icon" class="size-6 text-blue-700" />
      </div>
      <!-- title -->
      <div class="flex flex-col items-center justify-center gap-1">
        <span
          :class="{
            'text-sm font-semibold text-ink-gray-8': text === 'sm',
            'text-base font-semibold text-ink-gray-8': text === 'md' || !text,
            'text-lg font-semibold text-ink-gray-8': text === 'lg',
          }"
        >
          {{ __(title) }}
        </span>
        <span
          v-if="descriptionText"
          :class="{
            'text-center text-xs text-ink-gray-6 max-w-xs': text === 'sm',
            'text-center text-sm text-ink-gray-6 max-w-xs':
              text === 'md' || !text,
            'text-center text-base text-ink-gray-6 max-w-xs': text === 'lg',
          }"
        >
          {{ __(descriptionText) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VNode, computed } from "vue";
interface Props {
  title: string;
  icon?: VNode | string;
  description?: string;
  variant?: "default" | "overlay" | "badge";
  text?: "sm" | "md" | "lg";
}

const props = withDefaults(defineProps<Props>(), {
  title: "No Data Found",
  icon: "",
  variant: "default",
  text: "lg",
});

const descriptionText = computed(() =>
  props.description !== undefined && props.description !== ""
    ? props.description
    : `Create new ${props.title
        .split(" ")[1]
        .toLocaleLowerCase()} using the Create button.`
);
</script>

<style lang="scss" scoped></style>
