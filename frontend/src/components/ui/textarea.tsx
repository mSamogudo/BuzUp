import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, rows, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      rows={rows}
      className={cn(
        "border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 flex w-full resize-y rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        // Duas diferencas em relacao ao shadcn de origem, ambas medidas:
        //
        // Sem `field-sizing-content`. A caixa crescer com o conteudo e bonito
        // num formulario curto; no editor de termos, com paginas de texto, a
        // pagina passava de 3 722 para 6 070 pixeis de altura.
        //
        // E a altura minima so se aplica quando ninguem pediu `rows`. As 29
        // caixas do editor de termos pedem `rows={2}` e ficavam todas a 112px,
        // que e o que somava esses 2 348 pixeis.
        rows === undefined && "min-h-28",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
