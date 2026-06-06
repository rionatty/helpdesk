<template>
  <div v-if="ticket.data" class="flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" class="-ms-0.5" />
      </template>
      <template #right-header>
        <CustomActions
          v-if="ticket.data._customActions"
          :actions="ticket.data._customActions"
        />
        <Button
          v-if="ticket.data.status !== 'Closed'"
          :label="__('Close')"
          theme="gray"
          variant="solid"
          @click="handleClose()"
        >
          <template #prefix>
            <LucideCheck class="size-4" />
          </template>
        </Button>
      </template>
    </LayoutHeader>
    <div class="flex overflow-hidden h-full w-full">
      <!-- Main Ticket Comm -->
      <section class="flex flex-col flex-1 w-full md:max-w-[calc(100%-382px)]">
        <TicketHeader />
        <TicketStatusStepper />
        <div v-if="canReopen" class="px-4 md:px-10 pt-3">
          <div
            class="flex flex-col md:flex-row md:items-center md:justify-between gap-3 px-4 py-3 rounded-lg border border-outline-amber-1 bg-surface-amber-1"
          >
            <div>
              <div class="font-medium text-ink-gray-8">
                {{ __("This ticket was closed recently") }}
              </div>
              <div class="text-sm text-ink-gray-6">
                {{
                  __(
                    "Still need help? Reopen and we'll pick up where we left off."
                  )
                }}
              </div>
            </div>
            <Button
              :label="__('Reopen ticket')"
              theme="gray"
              variant="solid"
              :loading="setValue.loading"
              @click="reopenTicket"
            />
          </div>
        </div>
        <div
          class="px-6 md:px-10 mt-6"
          v-if="outsideHourSettings.data?.show && !isDismissed"
        >
          <Alert
            v-if="outsideHourSettings.data?.show"
            :title="outsideHourSettings.data?.msg"
            theme="yellow"
            class="text-p-sm [&_.size-4]:relative [&>.size-4]:top-[3.5px] [&_button>:first-child]:top-[2.25px] border border-amber-200"
            @dismiss="dismissBanner"
          >
          </Alert>
        </div>
        <!-- show for only mobile -->
        <TicketCustomerTemplateFields v-if="isMobileView" />

        <TicketConversation class="grow" />
        <div v-if="showEditor" class="px-5 pt-2 pb-1">
          <TypingIndicator :ticketId="props.ticketId" />
        </div>
        <div
          v-if="showEditor && isExpanded"
          class="px-5 pb-2 flex flex-wrap gap-2"
        >
          <Button
            v-for="snippet in cannedReplies"
            :key="snippet.label"
            theme="gray"
            variant="subtle"
            size="sm"
            :label="snippet.label"
            @click="applyCannedReply(snippet.text)"
          />
        </div>
        <div
          class="w-full p-5 relative"
          @keydown.ctrl.enter.capture.stop="sendEmail"
          @keydown.meta.enter.capture.stop="sendEmail"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDrop"
        >
          <div
            v-if="isDragging"
            class="absolute inset-2 z-10 bg-surface-blue-1/80 border-2 border-dashed border-blue-400 rounded-md flex items-center justify-center pointer-events-none"
          >
            <div class="text-base text-blue-700 font-medium">
              {{ __("Drop to attach") }}
            </div>
          </div>
          <TicketTextEditor
            v-if="showEditor"
            ref="editor"
            v-model:attachments="attachments"
            v-model:content="editorContent"
            v-model:expand="isExpanded"
            :placeholder="__('Type a message')"
            autofocus
            @clear="() => (isExpanded = false)"
            :uploadFunction="
              (file: any) => uploadFunction(file, 'HD Ticket', props.ticketId)
            "
          >
            <template #bottom-right>
              <Button
                :label="__('Send')"
                theme="gray"
                variant="solid"
                :disabled="$refs.editor?.editor.isEmpty || send.loading"
                :loading="send.loading"
                @click="sendEmail"
              />
            </template>
          </TicketTextEditor>
        </div>
      </section>
      <!-- Ticket Sidebar only for desktop view-->
      <TicketCustomerSidebar v-if="!isMobileView" @open="isExpanded = true" />
    </div>
    <TicketFeedback v-model:open="showFeedbackDialog" />
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import TicketCustomerSidebar from "@/components/ticket/TicketCustomerSidebar.vue";
import { setupCustomizations } from "@/composables/formCustomisation";
import { useActiveViewers } from "@/composables/realtime";
import { useScreenSize } from "@/composables/screen";

import { useConfigStore } from "@/stores/config";
import { globalStore } from "@/stores/globalStore";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { __ } from "@/translation";
import { isContentEmpty, isCustomerPortal, uploadFunction } from "@/utils";
import {
  Alert,
  Breadcrumbs,
  Button,
  call,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  provide,
  ref,
  watch,
} from "vue";
import { useRouter } from "vue-router";
import { ITicket } from "./symbols";
import TicketConversation from "./TicketConversation.vue";
import TicketCustomerTemplateFields from "./TicketCustomerTemplateFields.vue";
import TicketFeedback from "./TicketFeedback.vue";
import TicketStatusStepper from "@/components/ticket/TicketStatusStepper.vue";
import TicketHeader from "@/components/ticket/TicketHeader.vue";
import TypingIndicator from "@/components/TypingIndicator.vue";
import { useTyping } from "@/composables/realtime";
const TicketTextEditor = defineAsyncComponent(
  () => import("./TicketTextEditor.vue")
);

interface P {
  ticketId: string;
}
const router = useRouter();
const props = defineProps<P>();

const { getStatus } = useTicketStatusStore();

const ticket = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.get_one",
  cache: ["Ticket", props.ticketId],
  params: {
    name: props.ticketId,
    is_customer_portal: isCustomerPortal.value,
  },
  auto: true,
  onSuccess: (data) => {
    data.status = getStatus(data.status)?.label_customer;
    setupCustomizations(ticket, {
      doc: data,
      call,
      router,
      toast,
      $dialog,
      updateField,
      createToast: toast.create,
    });
  },
  onError: () => {
    toast.error(__("Ticket not found."));
    router.replace("/my-tickets");
  },
});

provide(ITicket, ticket);
const editor = ref(null);
const editorContent = ref("");
const attachments = ref([]);
const showFeedbackDialog = ref(false);
const isExpanded = ref(false);

const { isMobileView } = useScreenSize();
const { $dialog, $socket } = globalStore();
const isDismissed = ref(false);
const isDragging = ref(false);

const cannedReplies = computed(() => [
  {
    label: __("Resolved on my end"),
    text: __("Looks resolved on my end — thanks for the help!"),
  },
  {
    label: __("Still broken"),
    text: __("It's still not working. Could you take another look?"),
  },
  {
    label: __("I have a question"),
    text: __("One quick follow-up question: "),
  },
]);

function applyCannedReply(text: string) {
  if (!editor.value?.editor) {
    editorContent.value = text;
    return;
  }
  const current = editorContent.value || "";
  const next = current && current !== "<p></p>" ? `${current} ${text}` : text;
  editor.value.editor.commands.setContent(next, true);
  editor.value.editor.commands.focus("end");
}

const { onUserType, stopTyping, cleanup: cleanupTyping } = useTyping(
  props.ticketId
);
watch(editorContent, (v) => {
  if (v && v !== "<p></p>") onUserType();
});

function onDragOver(e: DragEvent) {
  if (e.dataTransfer?.types.includes("Files")) {
    isDragging.value = true;
  }
}
function onDragLeave(e: DragEvent) {
  if (e.target === e.currentTarget) isDragging.value = false;
}
async function onDrop(e: DragEvent) {
  isDragging.value = false;
  const files = e.dataTransfer?.files;
  if (!files?.length) return;
  for (const f of Array.from(files)) {
    try {
      const result = await uploadFunction(f, "HD Ticket", props.ticketId);
      if (result) attachments.value = [...attachments.value, result];
    } catch (_) {
      toast.error(__("Failed to attach {0}", [f.name]));
    }
  }
}

function getTodayKey() {
  return new Date().toISOString().split("T")[0];
}

function dismissBanner() {
  try {
    const todayKey = getTodayKey();
    localStorage.setItem(`dismissBanner_${props.ticketId}_${todayKey}`, "true");
    isDismissed.value = true;
  } catch (error) {
    console.error("Error saving banner dismissal:", error);
  }
}

onMounted(() => {
  try {
    const todayKey = getTodayKey();
    const dismissed = localStorage.getItem(
      `dismissBanner_${props.ticketId}_${todayKey}`
    );
    isDismissed.value = dismissed === "true";
    cleanupOldBannerDismissals();
  } catch (error) {
    console.error("Error reading banner dismissal:", error);
  }
});

// Clean up old banner dismissal localStorage keys
const cleanupOldBannerDismissals = () => {
  const CLEANUP_KEY = "lastBannerCleanup";
  const ONE_WEEK_MS = 7 * 24 * 60 * 60 * 1000;

  try {
    const lastCleanup = localStorage.getItem(CLEANUP_KEY);
    const now = Date.now();

    if (lastCleanup && now - parseInt(lastCleanup) < ONE_WEEK_MS) {
      return;
    }

    // Find and remove all dismissBanner keys
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("dismissBanner_")) {
        keysToRemove.push(key);
      }
    }

    // Remove the keys
    keysToRemove.forEach((key) => localStorage.removeItem(key));

    // Update last cleanup timestamp
    localStorage.setItem(CLEANUP_KEY, now.toString());
  } catch (error) {
    console.error("Error cleaning up banner dismissals:", error);
  }
};

const outsideHourSettings = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.show_outside_hours_banner",
  cache: ["OutsideHourBanner", props.ticketId],
  params: {
    ticket_name: props.ticketId,
  },
  auto: true,
});

const send = createResource({
  url: "run_doc_method",
  debounce: 300,
  makeParams: () => ({
    dt: "HD Ticket",
    dn: props.ticketId,
    method: "create_communication_via_contact",
    args: {
      message: editorContent.value,
      attachments: attachments.value,
    },
  }),
  onSuccess: () => {
    editor.value.editor.commands.clearContent(true);
    attachments.value = [];
    isExpanded.value = false;
    ticket.reload();
  },
});

function updateField(name, value, callback = () => {}) {
  updateTicket(name, value);
  callback();
}

function sendEmail() {
  if (isContentEmpty(editorContent.value) || send.loading) {
    return;
  }
  stopTyping();
  send.submit();
}

function updateTicket(fieldname: string, value: string) {
  createResource({
    url: "frappe.client.set_value",
    params: {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname,
      value,
    },
    auto: true,
    onSuccess: () => {
      ticket.reload();
      toast.success(__("Ticket updated successfully."));
    },
  });
}

function handleClose() {
  if (showFeedback.value) {
    showFeedbackDialog.value = true;
  } else {
    showConfirmationDialog();
  }
}

function showConfirmationDialog() {
  $dialog({
    title: __("Close Ticket"),
    message: __("Are you sure you want to close this ticket?"),
    actions: [
      {
        label: __("Confirm"),
        variant: "solid",
        onClick(close: Function) {
          ticket.data.status = "Closed";
          setValue.submit(
            { fieldname: "status", value: "Closed" },
            {
              onSuccess: () => {
                toast.success(__("Ticket closed successfully."));
              },
            }
          );
          close();
        },
      },
    ],
  });
}

const setValue = createResource({
  url: "frappe.client.set_value",
  debounce: 300,
  makeParams: (params) => {
    return {
      doctype: "HD Ticket",
      name: props.ticketId,
      fieldname: params.fieldname,
      value: params.value,
    };
  },
  onSuccess: () => {
    showFeedbackDialog.value = false;
    ticket.reload();
  },
});

const breadcrumbs = computed(() => {
  let items = [{ label: __("Tickets"), route: { name: "TicketsCustomer" } }];
  items.push({
    label: ticket.data?.subject,
    route: { name: "TicketCustomer" },
  });
  return items;
});

const showEditor = computed(() => ticket.data.status !== "Closed");

const REOPEN_WINDOW_DAYS = 7;
const canReopen = computed(() => {
  if (ticket.data?.status !== "Closed") return false;
  const closedAt = ticket.data.resolution_date || ticket.data.modified;
  if (!closedAt) return false;
  return dayjs(closedAt).isAfter(dayjs().subtract(REOPEN_WINDOW_DAYS, "day"));
});

function reopenTicket() {
  setValue.submit(
    { fieldname: "status", value: "Open" },
    {
      onSuccess: () => {
        toast.success(__("Ticket reopened"));
        ticket.reload();
      },
    }
  );
}

// this handles whether the ticket was raised and then was closed without any reply from the agent.
const { isFeedbackMandatory } = useConfigStore();
const showFeedback = computed(() => {
  const hasAgentCommunication = ticket.data?.communications?.some(
    (c) => c.sender !== ticket.data.raised_by
  );
  return hasAgentCommunication && isFeedbackMandatory;
});

const csatPromptKey = `csat_prompted_${props.ticketId}`;
watch(
  [() => ticket.data?.status, () => ticket.data?.feedback, showFeedback],
  ([status, feedback, canPrompt]) => {
    if (!status || !canPrompt || feedback) return;
    if (getStatus(status)?.category !== "Resolved") return;
    if (sessionStorage.getItem(csatPromptKey)) return;
    sessionStorage.setItem(csatPromptKey, "1");
    showFeedbackDialog.value = true;
  },
  { immediate: true }
);

const { startViewing, stopViewing } = useActiveViewers(props.ticketId);

onMounted(() => {
  startViewing(props.ticketId);
  document.title = props.ticketId;

  $socket.on("helpdesk:ticket-update", ({ ticket_id }) => {
    if (ticket_id == props.ticketId) {
      ticket.reload();
    }
  });
});

onUnmounted(() => {
  stopViewing(props.ticketId);
  cleanupTyping();
  document.title = "Helpdesk";
  $socket.off("helpdesk:ticket-update");
});
</script>
