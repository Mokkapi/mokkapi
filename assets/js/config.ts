export function getAppConfig(): { apiPrefix: string } {
  const el = document.getElementById("app-config");
  if (el) {
    return JSON.parse(el.textContent!);
  }

  throw new Error("Missing application config!");
}
