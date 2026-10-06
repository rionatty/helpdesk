<template>
  <div class="flex flex-col gap-1">
    <div class="relative rounded-md border border-outline-gray-3 bg-white">
      <canvas
        ref="canvas"
        class="block h-40 w-full cursor-crosshair touch-none"
        @pointerdown="start"
        @pointermove="move"
        @pointerup="end"
        @pointerleave="end"
        @pointercancel="end"
      />
      <span
        v-if="empty"
        class="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-ink-gray-4"
      >
        {{ __("Sign here") }}
      </span>
    </div>
    <div class="flex justify-end">
      <Button size="sm" variant="ghost" :label="__('Clear')" :disabled="empty" @click="clear" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Button } from "frappe-ui";
import { __ } from "@/translation";

// A signature drawn with a finger, pen or mouse, exported as a PNG data URL.
const canvas = ref<HTMLCanvasElement | null>(null);
const empty = ref(true);
let ctx: CanvasRenderingContext2D | null = null;
let last: { x: number; y: number } | null = null;

// Size the drawing surface to the element (sharp on high-density screens).
// Resizing a canvas wipes it, so this is also how it is cleared.
function setup() {
  const el = canvas.value;
  if (!el) return;
  const rect = el.getBoundingClientRect();
  if (!rect.width || !rect.height) return; // not laid out yet (dialog opening)
  const ratio = Math.max(window.devicePixelRatio || 1, 1);
  el.width = Math.round(rect.width * ratio);
  el.height = Math.round(rect.height * ratio);
  ctx = el.getContext("2d");
  if (!ctx) return;
  ctx.scale(ratio, ratio);
  ctx.lineWidth = 2.2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#111827";
  empty.value = true;
}

function at(e: PointerEvent) {
  const rect = canvas.value!.getBoundingClientRect();
  return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

function start(e: PointerEvent) {
  if (!ctx) setup();
  if (!ctx) return;
  canvas.value?.setPointerCapture(e.pointerId);
  last = at(e);
  // A tap leaves a dot.
  ctx.beginPath();
  ctx.moveTo(last.x, last.y);
  ctx.lineTo(last.x + 0.1, last.y + 0.1);
  ctx.stroke();
  empty.value = false;
}

function move(e: PointerEvent) {
  if (!ctx || !last) return;
  const p = at(e);
  ctx.beginPath();
  ctx.moveTo(last.x, last.y);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
  last = p;
}

function end() {
  last = null;
}

function clear() {
  setup();
}

function toDataURL(): string | null {
  return empty.value || !canvas.value ? null : canvas.value.toDataURL("image/png");
}

onMounted(() => requestAnimationFrame(setup));

defineExpose({ toDataURL, clear, isEmpty: () => empty.value });
</script>
