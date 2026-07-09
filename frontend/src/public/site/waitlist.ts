/* Tiny event bus so any marketing CTA can open the single app-waitlist modal
   without prop-drilling through six standalone route components. */
const EVENT = "buzup:open-waitlist";

export function openWaitlist() {
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function onOpenWaitlist(handler: () => void) {
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}
