import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { UiPreferencesProvider } from "./ui/UiPreferences";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <UiPreferencesProvider>
        <App />
      </UiPreferencesProvider>
    </BrowserRouter>
  </React.StrictMode>
);

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
