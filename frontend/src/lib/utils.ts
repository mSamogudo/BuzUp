import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Junta classes condicionais e resolve conflitos do Tailwind.
 *  Os componentes shadcn importam-na como `@/lib/utils`; aqui o `lib/` ja
 *  existia com outra coisa, por isso vive em `cn.ts` e o alias aponta para ca. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
