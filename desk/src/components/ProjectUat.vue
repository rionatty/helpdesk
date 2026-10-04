<template>
  <div
    v-if="editable || scripts.data?.length"
    class="executive-card flex flex-col gap-4 p-5"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <LucideClipboardList class="size-5 text-ink-gray-7" />
        <h3 class="text-lg font-semibold text-ink-gray-9">
          {{ __("User acceptance testing") }}
        </h3>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="overall.total" class="text-sm text-ink-gray-6">
          {{ __("{0} of {1} scripts passed", [overall.passed, overall.total]) }}
        </span>
        <Button
          v-if="editable"
          variant="subtle"
          :label="__('New script')"
          @click="openEditor()"
        >
          <template #prefix><LucidePlus class="size-4" /></template>
        </Button>
      </div>
    </div>

    <div
      v-if="overall.total"
      class="flex h-2 overflow-hidden rounded-full bg-surface-gray-2"
      :title="overallTitle"
    >
      <div class="bg-emerald-500" :style="seg(overall.passed, overall.total)" />
      <div class="bg-red-500" :style="seg(overall.failed, overall.total)" />
      <div class="bg-amber-500" :style="seg(overall.blocked, overall.total)" />
      <div class="bg-blue-400" :style="seg(overall.inProgress, overall.total)" />
    </div>

    <p
      v-if="!editable"
      class="text-sm text-ink-gray-6"
    >
      {{
        __(
          "Run each script and mark every step passed or failed. If something fails, say what happened: the team is told straight away and will let you know when it's ready to test again."
        )
      }}
    </p>

    <label
      v-if="!editable && hasMine"
      class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-7"
    >
      <input v-model="onlyMine" type="checkbox" class="size-4 accent-blue-600" />
      {{ __("Only the scripts assigned to me") }}
    </label>

    <p
      v-if="editable && scripts.data && !scripts.data.length"
      class="text-sm text-ink-gray-6"
    >
      {{
        __(
          "No test scripts yet. Write the steps the client should run before go-live. They see a script once you mark it ready for testing."
        )
      }}
    </p>

    <ul
      v-if="shown.length"
      class="flex flex-col divide-y divide-outline-gray-1 rounded-md border border-outline-gray-1"
    >
      <li
        v-for="s in shown"
        :key="s.name"
        class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center"
      >
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="truncate font-medium text-ink-gray-9" :title="s.title">
              {{ s.title }}
            </span>
            <Badge
              variant="subtle"
              :label="__(s.status)"
              :theme="statusTheme(s.status)"
            />
            <Badge
              v-if="editable && !s.ready_for_testing"
              variant="outline"
              theme="gray"
              :label="__('Draft')"
            />
            <Badge
              v-if="s.counts.retest"
              variant="subtle"
              theme="blue"
              :label="__('{0} to retest', [s.counts.retest])"
            />
          </div>
          <div class="mt-0.5 flex flex-wrap gap-x-3 text-xs text-ink-gray-5">
            <span v-if="s.area">{{ s.area }}</span>
            <span v-if="s.milestone_title">{{ s.milestone_title }}</span>
            <span v-if="s.tester">{{ __("Tester: {0}", [s.tester]) }}</span>
            <span v-if="editable && s.responsible_agent_name">
              {{ __("Defects to: {0}", [s.responsible_agent_name]) }}
            </span>
            <span>
              {{ __("{0} of {1} steps passed", [s.counts.passed, s.counts.total]) }}
            </span>
          </div>
          <div
            class="mt-1.5 flex h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-surface-gray-2"
          >
            <div class="bg-emerald-500" :style="seg(s.counts.passed, s.counts.total)" />
            <div class="bg-red-500" :style="seg(s.counts.failed, s.counts.total)" />
            <div class="bg-amber-500" :style="seg(s.counts.blocked, s.counts.total)" />
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1.5">
          <Button
            size="sm"
            :variant="editable ? 'subtle' : 'solid'"
            :label="runLabel(s)"
            @click="openRunner(s)"
          >
            <template #prefix><LucideListChecks class="size-3.5" /></template>
          </Button>
          <template v-if="editable">
            <Button
              size="sm"
              variant="ghost"
              :aria-label="__('Edit script')"
              :title="__('Edit script')"
              @click="openEditor(s)"
            >
              <LucidePencil class="size-3.5" />
            </Button>
            <Dropdown :options="menuFor(s)">
              <Button size="sm" variant="ghost" :aria-label="__('More actions')">
                <LucideMoreHorizontal class="size-3.5" />
              </Button>
            </Dropdown>
          </template>
        </div>
      </li>
    </ul>

    <!-- Run a script -->
    <Dialog
      v-model="showRunner"
      :options="{ title: runner.data?.title || __('Test script'), size: '3xl' }"
    >
      <template #body-content>
        <div v-if="!runner.data" class="py-10 text-center text-sm text-ink-gray-5">
          {{ __("Loading...") }}
        </div>
        <div v-else class="flex flex-col gap-4">
          <div class="flex flex-wrap items-center gap-2 text-sm">
            <Badge
              variant="subtle"
              :label="__(runner.data.status)"
              :theme="statusTheme(runner.data.status)"
            />
            <span class="text-ink-gray-6">
              {{ __("{0} of {1} steps done", [stepsDone, runner.data.counts.total]) }}
            </span>
            <span v-if="runner.data.area" class="text-ink-gray-5">
              · {{ runner.data.area }}
            </span>
          </div>

          <div
            v-if="runner.data.instructions"
            class="rounded-md bg-surface-gray-1 p-3 text-sm text-ink-gray-8"
          >
            <div class="mb-1 text-xs font-medium uppercase text-ink-gray-5">
              {{ __("Before you start") }}
            </div>
            <div class="whitespace-pre-wrap">{{ runner.data.instructions }}</div>
          </div>

          <ol class="flex flex-col gap-3">
            <li
              v-for="st in runner.data.steps"
              :key="st.name"
              class="rounded-lg border p-3"
              :class="stepBorder(st)"
            >
              <div class="flex items-start gap-3">
                <span
                  class="flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
                  :class="stepBadge(st)"
                >
                  {{ st.idx }}
                </span>
                <div class="flex min-w-0 flex-1 flex-col gap-2">
                  <div class="whitespace-pre-wrap break-words text-sm text-ink-gray-9">
                    {{ st.action }}
                  </div>
                  <div v-if="st.expected" class="text-sm text-ink-gray-6">
                    <span class="font-medium text-ink-gray-7">{{ __("Expected:") }}</span>
                    {{ " " }}
                    <span class="whitespace-pre-wrap break-words">{{ st.expected }}</span>
                  </div>

                  <div
                    v-if="st.outcome !== 'Not run'"
                    class="flex flex-wrap items-center gap-2 text-xs"
                  >
                    <Badge
                      variant="subtle"
                      :label="__(st.outcome)"
                      :theme="outcomeTheme(st.outcome)"
                    />
                    <span class="text-ink-gray-5">
                      {{ st.tested_by_name }} · {{ when(st.tested_on) }}
                    </span>
                    <span v-if="st.defect === 'Open'" class="text-ink-gray-6">
                      · {{ __("The team has been told") }}
                    </span>
                    <span v-if="editable && st.defect_task" class="text-ink-gray-5">
                      · {{ __("Defect task {0}", [st.defect_task]) }}
                    </span>
                  </div>
                  <div
                    v-else-if="st.retest"
                    class="flex items-center gap-1.5 text-xs font-medium text-blue-700"
                  >
                    <LucideRefreshCw class="size-3.5" />
                    {{
                      st.defect === "Fixed"
                        ? __("Fixed: please test this step again")
                        : __("Ready to test again")
                    }}
                  </div>
                  <p
                    v-if="st.note"
                    class="whitespace-pre-wrap break-words rounded bg-surface-gray-1 px-2 py-1 text-xs text-ink-gray-7"
                  >
                    {{ st.note }}
                  </p>

                  <div class="flex flex-wrap items-center gap-1.5">
                    <Button
                      size="sm"
                      theme="green"
                      :variant="st.outcome === 'Passed' ? 'solid' : 'subtle'"
                      :label="__('Passed')"
                      :loading="busy === `${st.name}:Passed`"
                      @click="record(st, 'Passed')"
                    >
                      <template #prefix><LucideCheck class="size-3.5" /></template>
                    </Button>
                    <Button
                      size="sm"
                      theme="red"
                      :variant="st.outcome === 'Failed' ? 'solid' : 'subtle'"
                      :label="__('Failed')"
                      @click="startProblem(st, 'Failed')"
                    >
                      <template #prefix><LucideCircleX class="size-3.5" /></template>
                    </Button>
                    <Button
                      size="sm"
                      theme="orange"
                      :variant="st.outcome === 'Blocked' ? 'solid' : 'subtle'"
                      :label="__('Blocked')"
                      :title="__('You could not run this step, e.g. data or access was missing')"
                      @click="startProblem(st, 'Blocked')"
                    >
                      <template #prefix><LucideCirclePause class="size-3.5" /></template>
                    </Button>
                    <Button
                      v-if="editable && st.outcome !== 'Not run'"
                      size="sm"
                      variant="ghost"
                      :label="__('Clear result')"
                      :loading="busy === `${st.name}:Not run`"
                      @click="record(st, 'Not run')"
                    />
                  </div>

                  <div
                    v-if="problemFor === st.name"
                    class="flex flex-col gap-2 rounded-md bg-surface-gray-1 p-2"
                  >
                    <FormControl
                      v-model="problemNote"
                      type="textarea"
                      :rows="3"
                      :placeholder="
                        problemOutcome === 'Failed'
                          ? __('What happened instead? Include any error message.')
                          : __('What stopped you from running this step?')
                      "
                    />
                    <div class="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        :label="__('Cancel')"
                        @click="problemFor = null"
                      />
                      <Button
                        size="sm"
                        variant="solid"
                        :theme="problemOutcome === 'Failed' ? 'red' : 'orange'"
                        :label="
                          problemOutcome === 'Failed'
                            ? __('Report the failure')
                            : __('Report the blocker')
                        "
                        :disabled="!problemNote.trim()"
                        :loading="busy === `${st.name}:${problemOutcome}`"
                        @click="record(st, problemOutcome, problemNote)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </li>
          </ol>

          <div
            v-if="stepsDone === runner.data.counts.total"
            class="rounded-md p-3 text-sm"
            :class="
              runner.data.status === 'Passed'
                ? 'bg-green-50 text-green-800'
                : 'bg-amber-50 text-amber-800'
            "
          >
            {{
              runner.data.status === "Passed"
                ? __("Every step passed. Thank you!")
                : __(
                    "Thank you. The team has the problems you reported, and will let you know when they are ready to test again."
                  )
            }}
          </div>
        </div>
      </template>
    </Dialog>

    <!-- New / edit a script (agents) -->
    <Dialog
      v-if="editable"
      v-model="showEditor"
      :options="{
        title: editor.name ? __('Edit test script') : __('New test script'),
        size: '3xl',
      }"
    >
      <template #body-content>
        <div class="flex flex-col gap-4">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl
              v-model="editor.title"
              class="sm:col-span-2"
              maxlength="140"
              :label="__('Title')"
              :placeholder="__('e.g. Create and post a sales invoice')"
            />
            <FormControl
              v-model="editor.area"
              maxlength="140"
              :label="__('Area')"
              :placeholder="__('e.g. Sales')"
            />
            <FormControl
              v-model="editor.milestone"
              type="select"
              :options="milestoneOptions"
              :label="__('Milestone')"
            />
            <FormControl
              v-model="editor.tester"
              type="email"
              :label="__('Tester (client email)')"
              :placeholder="__('Who at the client runs this')"
            />
            <FormControl
              v-model="editor.responsible_agent"
              type="select"
              :options="agentOptions"
              :label="__('Defects go to')"
            />
            <FormControl
              v-model="editor.instructions"
              class="sm:col-span-2"
              type="textarea"
              :rows="2"
              :label="__('Before you start (optional)')"
              :placeholder="__('Test data, logins, anything that must be set up first')"
            />
          </div>

          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("Steps") }}
              </span>
              <Button
                size="sm"
                variant="ghost"
                :label="showPaste ? __('Close') : __('Paste from a spreadsheet')"
                @click="showPaste = !showPaste"
              >
                <template #prefix><LucideClipboardList class="size-3.5" /></template>
              </Button>
            </div>
            <div
              v-if="showPaste"
              class="flex flex-col gap-2 rounded-md bg-surface-gray-1 p-3"
            >
              <p class="text-xs text-ink-gray-6">
                {{
                  __(
                    "One step per line. Separate the action from the expected result with a tab (as copied from a spreadsheet) or with |."
                  )
                }}
              </p>
              <FormControl v-model="pasteText" type="textarea" :rows="5" />
              <div class="flex justify-end">
                <Button
                  size="sm"
                  variant="solid"
                  :label="__('Add {0} steps', [pasted.length])"
                  :disabled="!pasted.length"
                  @click="addPasted"
                />
              </div>
            </div>
            <ol class="flex flex-col gap-2">
              <li
                v-for="(st, i) in editor.steps"
                :key="st.key"
                class="flex items-start gap-2 rounded-md border border-outline-gray-1 p-2"
              >
                <span class="mt-1.5 w-6 shrink-0 text-center text-xs font-semibold text-ink-gray-5">
                  {{ i + 1 }}
                </span>
                <div class="grid min-w-0 flex-1 grid-cols-1 gap-2 sm:grid-cols-2">
                  <FormControl
                    v-model="st.action"
                    type="textarea"
                    :rows="2"
                    :placeholder="__('Action: what the tester does')"
                  />
                  <FormControl
                    v-model="st.expected"
                    type="textarea"
                    :rows="2"
                    :placeholder="__('Expected result')"
                  />
                </div>
                <div class="flex shrink-0 flex-col">
                  <Button
                    size="sm"
                    variant="ghost"
                    :disabled="i === 0"
                    :aria-label="__('Move up')"
                    @click="move(i, -1)"
                  >
                    <LucideChevronUp class="size-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    :disabled="i === editor.steps.length - 1"
                    :aria-label="__('Move down')"
                    @click="move(i, 1)"
                  >
                    <LucideChevronDown class="size-3.5" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    :aria-label="__('Remove step')"
                    @click="editor.steps.splice(i, 1)"
                  >
                    <LucideTrash2 class="size-3.5" />
                  </Button>
                </div>
              </li>
            </ol>
            <Button
              class="self-start"
              size="sm"
              variant="subtle"
              :label="__('Add step')"
              @click="addStep()"
            >
              <template #prefix><LucidePlus class="size-3.5" /></template>
            </Button>
          </div>

          <div class="flex flex-col gap-2 rounded-md border border-outline-gray-1 p-3">
            <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8">
              <input
                v-model="editor.ready_for_testing"
                type="checkbox"
                class="size-4 accent-blue-600"
              />
              {{ __("Ready for testing: the client can see and run it") }}
            </label>
            <label
              v-if="editor.ready_for_testing && editor.tester"
              class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8"
            >
              <input
                v-model="editor.notify_tester"
                type="checkbox"
                class="size-4 accent-blue-600"
              />
              {{ __("Email {0} that it is ready", [editor.tester]) }}
            </label>
          </div>
        </div>
      </template>
      <template #actions>
        <div class="flex w-full justify-end gap-2">
          <Button :label="__('Cancel')" @click="showEditor = false" />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saveRes.loading"
            @click="save"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  Badge,
  Button,
  Dialog,
  Dropdown,
  FormControl,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import { __ } from "@/translation";
import LucideClipboardList from "~icons/lucide/clipboard-list";
import LucidePlus from "~icons/lucide/plus";
import LucideListChecks from "~icons/lucide/list-checks";
import LucidePencil from "~icons/lucide/pencil";
import LucideMoreHorizontal from "~icons/lucide/more-horizontal";
import LucideCheck from "~icons/lucide/check";
import LucideCircleX from "~icons/lucide/circle-x";
import LucideCirclePause from "~icons/lucide/circle-pause";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideChevronUp from "~icons/lucide/chevron-up";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideTrash2 from "~icons/lucide/trash-2";

const props = defineProps<{ projectId: string; editable?: boolean }>();
// Results and defects change the project's tasks and milestones.
const emit = defineEmits<{ (e: "changed"): void }>();

const authStore = useAuthStore();
const { $dialog } = globalStore();

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

const scripts = createResource({
  url: "helpdesk.api.uat.get_scripts",
  makeParams: () => ({ project: props.projectId }),
  // The section is optional on the client's page: degrade quietly.
  onError: (e: any) => console.warn("[helpdesk] UAT scripts:", e),
});
watch(
  () => props.projectId,
  (id) => id && scripts.reload(),
  { immediate: true }
);

const onlyMine = ref(false);
const me = computed(() => (authStore.userId || "").toLowerCase());
const hasMine = computed(() =>
  (scripts.data || []).some((s: any) => (s.tester || "").toLowerCase() === me.value)
);
const shown = computed<any[]>(() =>
  (scripts.data || []).filter(
    (s: any) => !onlyMine.value || (s.tester || "").toLowerCase() === me.value
  )
);

const overall = computed(() => {
  const list = scripts.data || [];
  const count = (status: string) => list.filter((s: any) => s.status === status).length;
  return {
    total: list.length,
    passed: count("Passed"),
    failed: count("Failed"),
    blocked: count("Blocked"),
    inProgress: count("In progress"),
  };
});
const overallTitle = computed(() =>
  __("{0} passed, {1} failed, {2} blocked, {3} in progress", [
    overall.value.passed,
    overall.value.failed,
    overall.value.blocked,
    overall.value.inProgress,
  ])
);

function seg(n: number, total: number) {
  return { width: total ? `${(n / total) * 100}%` : "0%" };
}

function statusTheme(status: string) {
  return (
    {
      Passed: "green",
      Failed: "red",
      Blocked: "orange",
      "In progress": "blue",
    } as Record<string, string>
  )[status] || "gray";
}

function outcomeTheme(outcome: string) {
  return statusTheme(outcome);
}

function runLabel(s: any) {
  if (props.editable) return __("Results");
  if (s.counts.retest) return __("Retest");
  if (s.status === "Not started") return __("Run");
  if (s.counts.not_run) return __("Continue");
  return __("View");
}

function changed() {
  scripts.reload();
  emit("changed");
}

// ---------------------------------------------------------------------------
// Running a script
// ---------------------------------------------------------------------------

const showRunner = ref(false);
const runnerFor = ref("");
const runner = createResource({
  url: "helpdesk.api.uat.get_script",
  makeParams: () => ({ name: runnerFor.value }),
  onError: (e: any) => {
    toast.error(e?.messages?.[0] || __("Could not open the test script"));
    showRunner.value = false;
  },
});

function openRunner(s: any) {
  runnerFor.value = s.name;
  runner.data = null;
  problemFor.value = null;
  showRunner.value = true;
  runner.reload();
}

const stepsDone = computed(
  () => (runner.data?.steps || []).filter((st: any) => st.outcome !== "Not run").length
);

const problemFor = ref<string | null>(null);
const problemOutcome = ref("Failed");
const problemNote = ref("");

function startProblem(st: any, outcome: string) {
  problemFor.value = st.name;
  problemOutcome.value = outcome;
  problemNote.value = st.outcome === outcome ? st.note || "" : "";
}

const busy = ref("");
const recordRes = createResource({
  url: "helpdesk.api.uat.record_result",
  onError: () => {},
});
async function record(st: any, outcome: string, note?: string) {
  busy.value = `${st.name}:${outcome}`;
  try {
    const payload = await recordRes.submit({
      script: runner.data.name,
      step: st.name,
      outcome,
      note: note || "",
    });
    runner.data = payload;
    problemFor.value = null;
    if (outcome === "Failed" || outcome === "Blocked") {
      toast.success(__("Reported. The team will put it right."));
    }
    changed();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the result"));
  } finally {
    busy.value = "";
  }
}

function stepBorder(st: any) {
  if (st.outcome === "Passed") return "border-green-200 bg-green-50/40";
  if (st.outcome === "Failed") return "border-red-200 bg-red-50/40";
  if (st.outcome === "Blocked") return "border-amber-200 bg-amber-50/40";
  if (st.retest) return "border-blue-200";
  return "border-outline-gray-2";
}

function stepBadge(st: any) {
  if (st.outcome === "Passed") return "bg-green-600 text-white";
  if (st.outcome === "Failed") return "bg-red-600 text-white";
  if (st.outcome === "Blocked") return "bg-amber-500 text-white";
  return "bg-surface-gray-3 text-ink-gray-8";
}

function when(d: string) {
  return d ? dayjs(d).format("D MMM, HH:mm") : "";
}

// ---------------------------------------------------------------------------
// Writing a script (agents)
// ---------------------------------------------------------------------------

const showEditor = ref(false);
let nextKey = 1;
const editor = reactive<Record<string, any>>({ steps: [] });

function stepRow(action = "", expected = "", name: string | null = null) {
  return { key: nextKey++, name, action, expected };
}

const milestones = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: props.projectId }),
});
const members = createResource({
  url: "helpdesk.api.project.get_project_members",
  makeParams: () => ({ project: props.projectId }),
});
const milestoneOptions = computed(() => [
  { label: __("None"), value: "" },
  ...(milestones.data || []).map((m: any) => ({ label: m.title, value: m.name })),
]);
const agentOptions = computed(() => [
  { label: __("The project lead"), value: "" },
  ...(members.data || []).map((m: any) => ({ label: m.agent_name, value: m.agent })),
]);

const loadScript = createResource({
  url: "helpdesk.api.uat.get_script",
  onError: () => {},
});

async function openEditor(s?: any) {
  if (!milestones.data) milestones.fetch();
  if (!members.data) members.fetch();
  Object.assign(editor, {
    name: null,
    title: "",
    area: "",
    milestone: "",
    tester: "",
    responsible_agent: "",
    instructions: "",
    ready_for_testing: false,
    notify_tester: true,
    steps: [stepRow()],
  });
  showPaste.value = false;
  pasteText.value = "";
  if (s) {
    try {
      const d = await loadScript.submit({ name: s.name });
      Object.assign(editor, {
        name: d.name,
        title: d.title || "",
        area: d.area || "",
        milestone: d.milestone || "",
        tester: d.tester || "",
        responsible_agent: d.responsible_agent || "",
        instructions: d.instructions || "",
        ready_for_testing: !!d.ready_for_testing,
        // Already ready: re-saving shouldn't email the tester again.
        notify_tester: !d.ready_for_testing,
        steps: d.steps.map((st: any) => stepRow(st.action, st.expected || "", st.name)),
      });
    } catch (e: any) {
      toast.error(e?.messages?.[0] || __("Could not open the test script"));
      return;
    }
  }
  showEditor.value = true;
}

function addStep() {
  editor.steps.push(stepRow());
}

function move(i: number, step: number) {
  const [row] = editor.steps.splice(i, 1);
  editor.steps.splice(i + step, 0, row);
}

const showPaste = ref(false);
const pasteText = ref("");
// "Action<TAB>Expected" (a spreadsheet copy) or "Action | Expected".
const pasted = computed(() =>
  pasteText.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.includes("\t") ? line.split("\t") : line.split("|");
      return {
        action: (parts[0] || "").trim(),
        expected: parts.slice(1).join(" ").trim(),
      };
    })
    .filter((row) => row.action)
);

function addPasted() {
  // Replace the single empty row a new script starts with.
  if (editor.steps.length === 1 && !editor.steps[0].action.trim()) editor.steps = [];
  for (const row of pasted.value) editor.steps.push(stepRow(row.action, row.expected));
  pasteText.value = "";
  showPaste.value = false;
}

const saveRes = createResource({
  url: "helpdesk.api.uat.save_script",
  onError: () => {},
});
async function save() {
  if (!editor.title.trim()) {
    toast.error(__("Give the test script a title"));
    return;
  }
  const steps = editor.steps
    .filter((st: any) => st.action.trim())
    .map((st: any) => ({ name: st.name, action: st.action, expected: st.expected }));
  if (!steps.length) {
    toast.error(__("Add at least one step"));
    return;
  }
  try {
    const result = await saveRes.submit({
      data: {
        name: editor.name,
        project: props.projectId,
        title: editor.title,
        area: editor.area,
        milestone: editor.milestone,
        tester: editor.tester,
        responsible_agent: editor.responsible_agent,
        instructions: editor.instructions,
        ready_for_testing: editor.ready_for_testing ? 1 : 0,
        notify_tester: editor.ready_for_testing && editor.notify_tester ? 1 : 0,
        steps,
      },
    });
    toast.success(
      result?.emailed
        ? __("Saved, and {0} was emailed", [result.emailed])
        : __("Test script saved")
    );
    showEditor.value = false;
    changed();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the test script"));
  }
}

// ---------------------------------------------------------------------------
// Script actions (agents)
// ---------------------------------------------------------------------------

function call(url: string, params: Record<string, any>, done: string) {
  return createResource({ url, onError: () => {} })
    .submit(params)
    .then(() => {
      toast.success(done);
      changed();
    })
    .catch((e: any) => toast.error(e?.messages?.[0] || __("That didn't work")));
}

function confirm(title: string, message: string, label: string, run: () => void) {
  $dialog({
    title,
    message,
    actions: [
      {
        label,
        theme: "red",
        variant: "solid",
        onClick: (close: Function) => {
          run();
          close();
        },
      },
    ],
  });
}

function menuFor(s: any) {
  const problems = s.counts.failed + s.counts.blocked;
  return [
    {
      label: s.ready_for_testing ? __("Back to draft") : __("Mark ready for testing"),
      onClick: () =>
        call(
          "helpdesk.api.uat.save_script",
          { data: { name: s.name, ready_for_testing: s.ready_for_testing ? 0 : 1 } },
          s.ready_for_testing ? __("Hidden from the client") : __("The client can now run it")
        ),
    },
    {
      label: __("Email the tester"),
      condition: () => !!(s.ready_for_testing && s.tester),
      onClick: () =>
        call("helpdesk.api.uat.email_tester", { name: s.name }, __("Email on its way to {0}", [s.tester])),
    },
    {
      label: __("Send failed steps back for retest"),
      condition: () => problems > 0,
      onClick: () =>
        call(
          "helpdesk.api.uat.reset_steps",
          { name: s.name, scope: "problems" },
          __("The client can test those steps again")
        ),
    },
    {
      label: __("Start a new test round"),
      condition: () => s.status !== "Not started",
      onClick: () =>
        confirm(
          __("Start a new test round"),
          __("Every step's result in {0} is cleared, so the script can be run again from the start.", [s.title]),
          __("Clear results"),
          () => call("helpdesk.api.uat.reset_steps", { name: s.name, scope: "all" }, __("Results cleared"))
        ),
    },
    {
      label: __("Duplicate"),
      onClick: () => call("helpdesk.api.uat.duplicate_script", { name: s.name }, __("Copy created as a draft")),
    },
    {
      label: __("Delete"),
      onClick: () =>
        confirm(
          __("Delete test script"),
          __("{0} and its results will be deleted. Defect tasks raised from it stay.", [s.title]),
          __("Delete"),
          () => call("helpdesk.api.uat.delete_script", { name: s.name }, __("Test script deleted"))
        ),
    },
  ];
}

defineExpose({ reload: () => scripts.reload() });
</script>
