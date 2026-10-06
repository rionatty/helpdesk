// Job cards print from a server-rendered page (helpdesk.api.job_card.
// print_job_card): plain A4 HTML the browser prints or saves as PDF. It opens
// in a new tab, so the agent's or client's page stays as it was.
export function printJobCard(name: string, autoprint = true) {
  const query = new URLSearchParams({ name });
  if (autoprint) query.set("autoprint", "1");
  window.open(
    `/api/method/helpdesk.api.job_card.print_job_card?${query.toString()}`,
    "_blank",
    "noopener"
  );
}
