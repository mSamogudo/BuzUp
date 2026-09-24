import type { ThemePreset } from "../tipos";

/** O preset da TPM-TUR no formato do customizador.
 *
 * GERADO a partir de `themes/tpm-tur.css`, que e a fonte de verdade: e de la
 * que sai o estado inicial da aplicacao. Este objecto existe para o
 * customizador poder VOLTAR a este tema depois de experimentar outro.
 *
 * Nao editar a mao. Correr:
 *
 *     python3 frontend/scripts/gerar-preset-tpm-tur.py
 *
 * de qualquer directorio. Os `color-mix()` do CSS ficam aqui resolvidos
 * em hexadecimal, porque o customizador trabalha com um mapa de cores e nao
 * com expressoes.
 */
export const tpmTurPreset: ThemePreset = {
  label: "TPM-TUR",
  styles: {
    light: {
        background: "#f7f7f7",
        foreground: "#212529",
        card: "#ffffff",
        "card-foreground": "#212529",
        popover: "#ffffff",
        "popover-foreground": "#212529",
        primary: "#00a1cd",
        "primary-foreground": "#022243",
        secondary: "#e8ecf1",
        "secondary-foreground": "#03316b",
        muted: "#eef1f5",
        "muted-foreground": "#6d6d6e",
        accent: "#e6eef5",
        "accent-foreground": "#03316b",
        warning: "#f9ae00",
        "warning-foreground": "#03316b",
        success: "#1d7a5f",
        "success-foreground": "#ffffff",
        destructive: "#b3261e",
        "destructive-foreground": "#ffffff",
        border: "#dfe5ec",
        input: "#c6d0dc",
        ring: "#0179aa",
        "chart-1": "#0179aa",
        "chart-2": "#c18a0b",
        "chart-3": "#1d7a5f",
        "chart-4": "#5b5aa8",
        "chart-5": "#c0603a",
        sidebar: "#03316b",
        "sidebar-foreground": "#a8c4e4",
        "sidebar-primary": "#00a1cd",
        "sidebar-primary-foreground": "#022243",
        "sidebar-accent": "#183f72",
        "sidebar-accent-foreground": "#ffffff",
        "sidebar-border": "#17396d",
        "sidebar-ring": "#00a1cd",
    },
    dark: {
        background: "#07182c",
        foreground: "#f7f7f7",
        card: "#0e2748",
        "card-foreground": "#f7f7f7",
        popover: "#0e2748",
        "popover-foreground": "#f7f7f7",
        primary: "#38b6d8",
        "primary-foreground": "#03203a",
        secondary: "#14355f",
        "secondary-foreground": "#f7f7f7",
        muted: "#0c2340",
        "muted-foreground": "#b4b4b4",
        accent: "#183f72",
        "accent-foreground": "#f7f7f7",
        warning: "#f9b700",
        "warning-foreground": "#2a1e02",
        success: "#4cc79f",
        "success-foreground": "#04241a",
        destructive: "#ff6b6b",
        "destructive-foreground": "#2a0a0a",
        border: "#1d4373",
        input: "#27548c",
        ring: "#38b6d8",
        "chart-1": "#38b6d8",
        "chart-2": "#f9b700",
        "chart-3": "#4cc79f",
        "chart-4": "#9b95e0",
        "chart-5": "#e08a63",
        sidebar: "#03142a",
        "sidebar-foreground": "#9fbde0",
        "sidebar-primary": "#38b6d8",
        "sidebar-primary-foreground": "#03203a",
        "sidebar-accent": "#13314f",
        "sidebar-accent-foreground": "#f7f7f7",
        "sidebar-border": "#16345c",
        "sidebar-ring": "#38b6d8",
    },
  },
};
