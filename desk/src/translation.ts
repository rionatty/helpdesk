import { createResource } from "frappe-ui";
import type { App } from "vue";

function getTranslatedMessage(message: string): string {
  const translatedMessages = (("translatedMessages" in window
    ? window["translatedMessages"]
    : null) ?? {}) as Record<string, string>;
  return translatedMessages[message] || message;
}

function translate(message: string): string;
function translate(
  message: string,
  ...args: (string | number | (string | number)[])[]
): string;
function translate(
  message: string,
  ...args: (string | number | (string | number)[])[]
): string {
  const translatedMessage = getTranslatedMessage(message);
  // Frappe-style calls pass replacements as one array: __("{0} of {1}", [a, b])
  const replacements =
    args.length === 1 && Array.isArray(args[0]) ? args[0] : args;
  if (replacements.length === 0) {
    return translatedMessage;
  }
  return translatedMessage.replace(/{(\d+)}/g, function (match, index) {
    return typeof replacements[index] != "undefined"
      ? String(replacements[index])
      : match;
  });
}

export const __ = translate;

function fetchTranslations() {
  createResource({
    url: "helpdesk.api.general.get_translations",
    method: "GET",
    cache: "translations",
    auto: true,
    transform(data: Record<string, string>) {
      (window as any).translatedMessages = data;
    },
  });
}

export function translationPlugin(app: App<Element>) {
  app.config.globalProperties.__ = translate;
  const windowObj = window as any;
  windowObj.__ = translate;
  if (!windowObj.translatedMessages) {
    fetchTranslations();
  }
}

declare module "@vue/runtime-core" {
  interface ComponentCustomProperties {
    __: typeof translate;
  }
}
