import { Outlet } from "react-router-dom";
import { WaitlistModal } from "./WaitlistModal";

/** Wraps the public marketing routes so the app-waitlist dialog is mounted
    exactly once and reachable from every "Baixar a app" CTA. */
export function PublicLayout() {
  return (
    <>
      <Outlet />
      {/* The .bz wrapper is required: the dialog styles and the design tokens
          (--blue etc.) are all scoped under .bz. Without it the dialog and its
          honeypot render as unstyled raw HTML. */}
      <div className="bz">
        <WaitlistModal />
      </div>
    </>
  );
}
