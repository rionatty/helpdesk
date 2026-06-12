<template>
  <div
    class="flex flex-col overflow-y-auto"
    :class="isCustomerPortal && 'bg-customer-portal'"
  >
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <CustomActions
          v-if="template.data?._customActions"
          :actions="template.data?._customActions"
        />
      </template>
    </LayoutHeader>
    <!-- Container -->
    <div
      class="flex flex-col gap-5 py-6 h-full flex-1 self-center overflow-auto mx-auto w-full max-w-4xl px-5"
    >
      <!-- Context banner (creating a ticket for an add-on / project) -->
      <div
        v-if="contextLabel"
        class="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800"
      >
        <lucide-package class="size-4 shrink-0" />
        {{ contextLabel }}
      </div>

      <!-- Customer-side hero -->
      <div
        v-if="isCustomerPortal"
        class="hd-brand-hero rounded-2xl px-6 py-6 md:px-8 flex items-center gap-4 mt-1 animate-in-fade"
      >
        <div
          class="hidden sm:flex size-12 rounded-2xl bg-white/10 border border-white/15 items-center justify-center shrink-0"
        >
          <lucide-life-buoy class="size-7 text-[var(--hd-gold)]" />
        </div>
        <div>
          <h1
            class="executive-heading text-2xl md:text-3xl text-white leading-tight"
          >
            {{ __("Hi there! How can we help you?") }}
          </h1>
          <p class="text-sm hd-on-navy-soft mt-1">
            {{
              __(
                "Tell us what's going on. We'll typically reply within a few hours."
              )
            }}
          </p>
        </div>
      </div>

      <!-- Form wrapper: elevated card on the customer portal -->
      <div
        :class="
          isCustomerPortal
            ? 'executive-card bg-surface-white p-5 md:p-7 flex flex-col gap-5 animate-in-fade'
            : 'flex flex-col gap-5'
        "
      >
      <!-- custom fields descriptions -->
      <div v-if="Boolean(template.data?.about)" class="">
        <div class="prose-f" v-html="sanitize(template.data.about)" />
      </div>
      <!-- custom fields -->
      <div
        class="grid grid-cols-1 gap-4 sm:grid-cols-3"
        v-if="Boolean(visibleFields)"
      >
        <UniInput
          v-for="field in visibleFields"
          :key="field.fieldname"
          :field="field"
          :value="templateFields[field.fieldname]"
          @change="
            (e) => handleOnFieldChange(e, field.fieldname, field.fieldtype)
          "
        >
          <template v-if="field.fieldname === 'priority'" #label-extra>
            <template
              v-if="
                ticketPriorityResource.dataMap[templateFields[field.fieldname]]
                  ?.description
              "
            >
              <Tooltip
                :text="
                  ticketPriorityResource.dataMap[
                    templateFields[field.fieldname]
                  ].description.trim()
                "
              >
                <lucide-circle-question-mark class="h-4 w-4 text-ink-gray-6" />
              </Tooltip>
            </template>
          </template>
        </UniInput>
      </div>
      <!-- Related project / add-on (optional) -->
      <div
        v-if="projectOptions.length > 1 || addonOptions.length > 1"
        class="grid grid-cols-1 gap-4 sm:grid-cols-2"
      >
        <div v-if="projectOptions.length > 1" class="flex flex-col gap-2">
          <span class="block text-sm font-medium text-ink-gray-7">
            {{ __("Related project") }}
          </span>
          <FormControl
            v-model="selectedProject"
            type="select"
            :options="projectOptions"
          />
        </div>
        <div v-if="addonOptions.length > 1" class="flex flex-col gap-2">
          <span class="block text-sm font-medium text-ink-gray-7">
            {{ __("Related add-on") }}
          </span>
          <FormControl
            v-model="selectedAddon"
            type="select"
            :options="addonOptions"
          />
        </div>
      </div>
      <!-- existing fields -->
      <div
        class="flex flex-col"
        :class="(subject.length >= 2 || description.length) && 'gap-5'"
      >
        <div class="flex flex-col gap-2">
          <span class="block text-sm font-medium text-ink-gray-7">
            {{ __("Subject") }}
            <span class="text-red-500"> * </span>
          </span>
          <FormControl
            v-model="subject"
            type="text"
            size="lg"
            :placeholder="__('e.g. Unable to log in to my account')"
            maxlength="140"
          />
        </div>
        <SearchArticles
          v-if="isCustomerPortal"
          :query="subject"
          class="shadow"
        />
        <div v-if="isCustomerPortal">
          <div
            v-show="subject.length <= 2 && description.length === 0"
            class="flex items-center gap-2 rounded-lg border border-dashed border-outline-gray-2 px-3 py-2.5 text-sm text-ink-gray-5"
          >
            <lucide-arrow-up class="size-4 shrink-0" />
            {{ __("Enter a subject above to describe your issue") }}
          </div>
          <TicketTextEditor
            v-show="subject.length > 2 || description.length > 0"
            ref="editor"
            v-model:attachments="attachments"
            v-model:content="description"
            :placeholder="__('Describe your issue in detail…')"
            expand
            :uploadFunction="(file:any)=>uploadFunction(file)"
          >
            <template #bottom-right>
              <Button
                :label="__('Submit ticket')"
                theme="blue"
                variant="solid"
                :disabled="
                  $refs.editor.editor.isEmpty || ticket.loading || !subject
                "
                :loading="ticket.loading"
                @click="() => ticket.submit()"
              >
                <template #prefix>
                  <lucide-send class="size-4" />
                </template>
              </Button>
            </template>
          </TicketTextEditor>
        </div>
      </div>
      </div>

      <!-- for agent portal -->
      <div v-if="!isCustomerPortal">
        <TicketTextEditor
          ref="editor"
          v-model:attachments="attachments"
          v-model:content="description"
          :placeholder="__('Detailed explanation')"
          expand
        >
          <template #bottom-right>
            <Button
              :label="__('Submit')"
              theme="gray"
              variant="solid"
              :disabled="
                $refs.editor.editor.isEmpty || ticket.loading || !subject
              "
              @click="() => ticket.submit()"
            />
          </template>
        </TicketTextEditor>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader, UniInput } from "@/components";
import {
  handleLinkFieldUpdate,
  handleSelectFieldUpdate,
  parseField,
  setupCustomizations,
} from "@/composables/formCustomisation";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import { capture } from "@/telemetry";
import { __ } from "@/translation";
import { Field } from "@/types";
import { isCustomerPortal, uploadFunction } from "@/utils";
import {
  Breadcrumbs,
  Button,
  call,
  createListResource,
  createResource,
  FormControl,
  usePageMeta,
} from "frappe-ui";
import { useOnboarding } from "frappe-ui/frappe";
import sanitizeHtml from "sanitize-html";
import { computed, defineAsyncComponent, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import SearchArticles from "../../components/SearchArticles.vue";

const TicketTextEditor = defineAsyncComponent(
  () => import("./TicketTextEditor.vue")
);

interface P {
  templateId?: string;
}

const props = withDefaults(defineProps<P>(), {
  templateId: "",
});

const route = useRoute();
const router = useRouter();

// When opened from an add-on / project ("New ticket"), show context + tag it.
const contextLabel = computed(() => {
  if (route.query.addon)
    return __("Creating a ticket for add-on: {0}", [route.query.addon]);
  if (route.query.project)
    return __("Creating a ticket for project: {0}", [route.query.project]);
  return "";
});
const { $dialog } = globalStore();
const { updateOnboardingStep } = useOnboarding("helpdesk");
const { isManager, userId: userID } = useAuthStore();
const subject = ref("");
const description = ref("");
const attachments = ref([]);
const templateFields = reactive({});

// Optional project / add-on link, prefilled from ?project= / ?addon=.
const selectedProject = ref((route.query.project as string) || "");
const selectedAddon = ref((route.query.addon as string) || "");
const projectsRes = createResource({
  url: "helpdesk.api.project.get_projects",
  auto: true,
});
const addonsRes = createResource({
  url: "helpdesk.api.addon.get_addons",
  auto: true,
});
const projectOptions = computed(() => [
  { label: __("None"), value: "" },
  ...(projectsRes.data || []).map((p: any) => ({
    label: p.project_name || p.name,
    value: p.name,
  })),
]);
const addonOptions = computed(() => [
  { label: __("None"), value: "" },
  ...(addonsRes.data || []).map((a: any) => ({
    label: a.addon_name || a.name,
    value: a.name,
  })),
]);

const template = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket_template.api.get_one",
  makeParams: () => ({
    name: props.templateId || "Default",
  }),
  auto: true,
  onSuccess: (data) => {
    description.value = data.description_template || "";
    oldFields = window.structuredClone(data.fields || []);
    setupCustomizations(template, {
      doc: templateFields,
      call,
      router,
      $dialog,
      applyFilters,
    });
    setupTemplateFields(data.fields);
  },
});

function setupTemplateFields(fields) {
  fields.forEach((field: Field) => {
    templateFields[field.fieldname] = "";
  });
}

const ticketPriorityResource = createListResource({
  doctype: "HD Ticket Priority",
  fields: ["name", "description"],
  auto: true,
  cache: "ticketPriorities",
});

let oldFields = [];

function applyFilters(fieldname: string, filters: any = null) {
  const f: Field = template.data.fields.find((f) => f.fieldname === fieldname);
  if (!f) return;
  if (f.fieldtype === "Select") {
    handleSelectFieldUpdate(f, fieldname, filters, templateFields, oldFields);
  } else if (f.fieldtype === "Link") {
    handleLinkFieldUpdate(f, fieldname, filters, templateFields, oldFields);
  }
}

const customOnChange = computed(() => template.data?._customOnChange);

const visibleFields = computed(() => {
  let _fields = template.data?.fields?.filter(
    (f) => !isCustomerPortal.value || !f.hide_from_customer
  );
  if (!_fields) return [];
  return _fields.map((field) => parseField(field, templateFields));
});

function handleOnFieldChange(e: any, fieldname: string, fieldtype: string) {
  templateFields[fieldname] = e.value;
  const fieldDependentFns = customOnChange.value?.[fieldname];
  if (fieldDependentFns) {
    fieldDependentFns.forEach((fn: Function) => {
      fn(e.value, fieldtype);
    });
  }
}

const ticket = createResource({
  url: "helpdesk.helpdesk.doctype.hd_ticket.api.new",
  debounce: 300,
  makeParams: () => ({
    doc: {
      description: description.value,
      subject: subject.value,
      template: props.templateId,
      ...(selectedAddon.value ? { addon: selectedAddon.value } : {}),
      ...(selectedProject.value ? { project: selectedProject.value } : {}),
      ...templateFields,
    },
    attachments: attachments.value,
  }),
  validate: (params) => {
    const fields = visibleFields.value?.filter((f) => f.required) || [];
    const toVerify = [...fields, "subject", "description"];
    for (const field of toVerify) {
      if (!params.doc[field.fieldname || field]) {
        return `${field.label || field} is required`;
      }
    }
  },
  onSuccess: (data) => {
    if (isManager) {
      updateOnboardingStep("create_first_ticket", true, false, () =>
        localStorage.setItem("firstTicket", data.name)
      );
    }
    if (isCustomerPortal.value) {
      $dialog({
        title: __("Ticket received"),
        message: __(
          "Thanks — your ticket #{0} is in our queue. A support agent will reply shortly.",
          [data.name]
        ),
        actions: [
          {
            label: __("View ticket"),
            variant: "solid",
            theme: "gray",
            onClick: (close: Function) => {
              close();
              router.push({
                name: "TicketCustomer",
                params: { ticketId: data.name },
              });
            },
          },
        ],
      });
    } else {
      router.push({
        name: "TicketAgent",
        params: { ticketId: data.name },
      });
    }
  },
});

function sanitize(html: string) {
  return sanitizeHtml(html, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
  });
}

const breadcrumbs = computed(() => {
  const items = [
    {
      label: __("Tickets"),
      route: {
        name: isCustomerPortal.value ? "TicketsCustomer" : "TicketsAgent",
      },
    },
    {
      label: __("New Ticket"),
      route: {
        name: "TicketNew",
      },
    },
  ];
  return items;
});

usePageMeta(() => ({
  title: __("New Ticket"),
}));

onMounted(() => {
  capture("new_ticket_page", {
    data: {
      user: userID,
    },
  });
});
</script>
