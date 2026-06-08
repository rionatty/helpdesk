<template>
  <div class="overflow-y-auto h-full bg-customer-portal flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideUserCog class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Account") }}
          </div>
        </div>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-2xl mx-auto px-4 md:px-6 py-6 flex flex-col gap-5 flex-1"
    >
      <!-- Profile -->
      <div class="executive-card p-6 flex flex-col gap-5">
        <div class="executive-heading text-lg text-ink-gray-9">
          {{ __("Profile") }}
        </div>

        <div class="flex items-center gap-4">
          <Avatar size="3xl" :label="form.full_name" :image="form.image" />
          <FileUploader
            :upload-args="{ private: false, optimize: true }"
            @success="onAvatar"
          >
            <template #default="{ openFileSelector, uploading }">
              <Button
                variant="subtle"
                :loading="uploading"
                @click="openFileSelector()"
              >
                <template #prefix><LucideCamera class="size-4" /></template>
                {{ __("Change photo") }}
              </Button>
            </template>
          </FileUploader>
        </div>

        <div class="flex flex-col gap-1.5">
          <span class="text-sm font-medium text-ink-gray-7">
            {{ __("Full name") }}
          </span>
          <FormControl v-model="form.full_name" type="text" size="md" />
        </div>

        <div class="flex flex-col gap-1.5">
          <span class="text-sm font-medium text-ink-gray-7">
            {{ __("Email") }}
          </span>
          <FormControl :modelValue="form.email" type="text" size="md" disabled />
        </div>

        <div class="flex flex-col gap-1.5">
          <span class="text-sm font-medium text-ink-gray-7">
            {{ __("Phone") }}
          </span>
          <FormControl
            v-model="form.phone"
            type="text"
            size="md"
            :placeholder="__('e.g. +1 555 123 4567')"
          />
        </div>

        <div class="flex justify-end">
          <Button
            variant="solid"
            theme="blue"
            :loading="saveProfile.loading"
            @click="onSaveProfile"
          >
            {{ __("Save changes") }}
          </Button>
        </div>
      </div>

      <!-- Notifications -->
      <div class="executive-card p-6 flex flex-col gap-4">
        <div class="executive-heading text-lg text-ink-gray-9">
          {{ __("Notifications") }}
        </div>

        <label class="flex items-center justify-between gap-4 cursor-pointer">
          <div>
            <div class="text-sm font-medium text-ink-gray-8">
              {{ __("Email me ticket updates") }}
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ __("Get an email when there's activity on your tickets.") }}
            </div>
          </div>
          <Switch v-model="form.email_updates" @update:modelValue="savePrefs" />
        </label>

        <label class="flex items-center justify-between gap-4 cursor-pointer">
          <div>
            <div class="text-sm font-medium text-ink-gray-8">
              {{ __("Send me product announcements") }}
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ __("Occasional news about new features and improvements.") }}
            </div>
          </div>
          <Switch
            v-model="form.product_announcements"
            @update:modelValue="savePrefs"
          />
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import {
  Avatar,
  Button,
  FileUploader,
  FormControl,
  Switch,
  createResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { LayoutHeader } from "@/components";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";
import LucideUserCog from "~icons/lucide/user-cog";
import LucideCamera from "~icons/lucide/camera";

const config = useConfigStore();

const form = reactive({
  full_name: "",
  email: "",
  phone: "",
  image: "",
  email_updates: true,
  product_announcements: false,
});

const profile = createResource({
  url: "helpdesk.api.profile.get_profile",
  auto: true,
  onSuccess: (d: any) => {
    form.full_name = d.full_name || "";
    form.email = d.email || "";
    form.phone = d.phone || "";
    form.image = d.image || "";
    form.email_updates = !!d.email_updates;
    form.product_announcements = !!d.product_announcements;
  },
});

const saveProfile = createResource({
  url: "helpdesk.api.profile.update_profile",
  onSuccess: () => toast.success(__("Profile updated")),
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update profile")),
});
function onSaveProfile() {
  saveProfile.submit({ full_name: form.full_name, phone: form.phone });
}

function onAvatar(file: any) {
  if (!file?.file_url) return;
  form.image = file.file_url;
  saveProfile.submit({ image: file.file_url });
}

const savePrefsRes = createResource({
  url: "helpdesk.api.profile.update_preferences",
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save preference")),
});
function savePrefs() {
  savePrefsRes.submit({
    email_updates: form.email_updates ? 1 : 0,
    product_announcements: form.product_announcements ? 1 : 0,
  });
}

usePageMeta(() => ({
  title: `${config.brandName || __("Support")} — ${__("Account")}`,
}));
</script>
