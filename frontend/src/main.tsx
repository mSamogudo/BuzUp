import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { HelmetProvider } from "react-helmet-async";
import App from "./App";
import { UiPreferencesProvider } from "./ui/UiPreferences";
import "./styles.css";

const rootEl = document.getElementById("root")!;

const tree = (
  <React.StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <UiPreferencesProvider>
          <App />
        </UiPreferencesProvider>
      </BrowserRouter>
    </HelmetProvider>
  </React.StrictMode>
);

// react-snap pre-renders static HTML into #root; hydrate it instead of
// throwing it away. Empty root (normal dev/prod load) → fresh render.
if (rootEl.hasChildNodes()) {
  ReactDOM.hydrateRoot(rootEl, tree);
} else {
  ReactDOM.createRoot(rootEl).render(tree);
}

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
