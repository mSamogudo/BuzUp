import { useCallback, useSyncExternalStore } from "react";

/** As três opções que o `Sidebar` do shadcn expõe e que o personalizador
 *  deixa mexer. Ficaram por fazer na fase 2 porque ainda não havia barra
 *  lateral shadcn para configurar. */
export type VarianteBarra = "sidebar" | "floating" | "inset";
export type RecolhaBarra = "offcanvas" | "icon" | "none";
export type LadoBarra = "left" | "right";

export interface LayoutBarra {
  variante: VarianteBarra;
  recolha: RecolhaBarra;
  lado: LadoBarra;
}

const CHAVE = "buzup_layout_barra";
const OMISSAO: LayoutBarra = { variante: "sidebar", recolha: "icon", lado: "left" };

export const VARIANTES: { valor: VarianteBarra; nome: string; nota: string }[] = [
  { valor: "sidebar", nome: "Encostada", nota: "Coluna fixa à margem" },
  { valor: "floating", nome: "Flutuante", nota: "Cartão destacado, com sombra" },
  { valor: "inset", nome: "Embutida", nota: "Conteúdo recuado em cartão" },
];

export const RECOLHAS: { valor: RecolhaBarra; nome: string; nota: string }[] = [
  { valor: "icon", nome: "Ícones", nota: "Encolhe e deixa os ícones" },
  { valor: "offcanvas", nome: "Sai", nota: "Desliza para fora do ecrã" },
  { valor: "none", nome: "Fixa", nota: "Nunca recolhe" },
];

export const LADOS: { valor: LadoBarra; nome: string }[] = [
  { valor: "left", nome: "Esquerda" },
  { valor: "right", nome: "Direita" },
];

function ler(): LayoutBarra {
  try {
    const cru = localStorage.getItem(CHAVE);
    if (!cru) return OMISSAO;
    const v = JSON.parse(cru) as Partial<LayoutBarra>;
    return {
      variante: VARIANTES.some((x) => x.valor === v.variante) ? v.variante! : OMISSAO.variante,
      recolha: RECOLHAS.some((x) => x.valor === v.recolha) ? v.recolha! : OMISSAO.recolha,
      lado: LADOS.some((x) => x.valor === v.lado) ? v.lado! : OMISSAO.lado,
    };
  } catch {
    return OMISSAO; // JSON estragado a mao: volta ao normal em vez de rebentar
  }
}

/* O personalizador e a casca vivem em ramos diferentes da arvore, por isso
 * partilham o estado por subscricao em vez de contexto: quem mexe avisa,
 * quem mostra volta a ler. Evita enfiar um provider so para tres opcoes. */
const ouvintes = new Set<() => void>();
let cache: LayoutBarra | null = null;

function instantaneo(): LayoutBarra {
  if (!cache) cache = ler();
  return cache;
}

function subscrever(aviso: () => void) {
  ouvintes.add(aviso);
  return () => ouvintes.delete(aviso);
}

function noServidor(): LayoutBarra {
  return OMISSAO;
}

export function useLayoutBarra() {
  const layout = useSyncExternalStore(subscrever, instantaneo, noServidor);

  const definir = useCallback((mudanca: Partial<LayoutBarra>) => {
    cache = { ...instantaneo(), ...mudanca };
    localStorage.setItem(CHAVE, JSON.stringify(cache));
    for (const aviso of ouvintes) aviso();
  }, []);

  const repor = useCallback(() => {
    cache = OMISSAO;
    localStorage.removeItem(CHAVE);
    for (const aviso of ouvintes) aviso();
  }, []);

  return { layout, definir, repor };
}
