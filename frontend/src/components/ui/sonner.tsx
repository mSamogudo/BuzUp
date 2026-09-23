import { Toaster as Sonner, type ToasterProps } from "sonner"

import { useUi } from "@/ui/UiPreferences"

/** Os avisos, vestidos pelo preset do operador.
 *
 *  Duas correccoes ao componente de origem:
 *
 *  O tema vem do `useUi()` desta aplicacao e nao do `next-themes`, que aqui
 *  nao esta montado — o `useTheme()` devolvia sempre `"system"` e o Sonner
 *  seguia a preferencia do sistema operativo em vez do interruptor do portal.
 *
 *  E as cores de estado sao mapeadas. Com `richColors` o Sonner traz a sua
 *  propria paleta: o aviso de erro saia a #e60000 sobre #fff0f0, que da
 *  4,35:1 e chumba AA, e nao acompanhava tema nenhum. */
const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useUi()

  return (
    <Sonner
      className="toaster group"
      richColors
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",

          "--error-bg": "color-mix(in srgb, var(--destructive) 10%, var(--popover))",
          "--error-text": "var(--destructive)",
          "--error-border": "color-mix(in srgb, var(--destructive) 30%, var(--popover))",

          "--success-bg": "color-mix(in srgb, var(--success) 10%, var(--popover))",
          "--success-text": "color-mix(in srgb, var(--success) 82%, var(--popover-foreground))",
          "--success-border": "color-mix(in srgb, var(--success) 30%, var(--popover))",

          "--warning-bg": "color-mix(in srgb, var(--warning) 12%, var(--popover))",
          "--warning-text": "var(--warning-foreground)",
          "--warning-border": "color-mix(in srgb, var(--warning) 34%, var(--popover))",

          "--info-bg": "color-mix(in srgb, var(--primary) 10%, var(--popover))",
          "--info-text": "var(--primary-ink)",
          "--info-border": "color-mix(in srgb, var(--primary) 30%, var(--popover))",
        } as React.CSSProperties
      }
      theme={theme}
      {...props}
    />
  )
}

export { Toaster }
