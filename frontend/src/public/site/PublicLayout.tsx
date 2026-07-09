import { Outlet } from "react-router-dom";
import { WaitlistModal } from "./WaitlistModal";

/** Wraps the public marketing routes so the app-waitlist dialog is mounted
    exactly once and reachable from every "Baixar a app" CTA. */
export function PublicLayout() {
  return (
    <>
      <Outlet />
      <WaitlistModal />
    </>
  );
}
