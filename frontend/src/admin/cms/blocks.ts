/**
 * Esquema de conteúdo por tipo de bloco.
 *
 * Fonte: docs/design-handoff/03-cms-especificacao.md §1.3 — incluindo os
 * limites de caracteres que o editor mostra no contador.
 */

export type FieldKind =
  | "text"
  | "textarea"
  | "list"      // lista de frases, uma por linha, por idioma
  | "richtext"  // HTML restrito: h2, h3, p, ul, ol, a, strong, em
  | "items"     // lista de objectos com sub-campos
  | "plans"     // referência a `plans`
  | "systems"   // referência a `eco_systems`
  | "media";    // referência a `media_assets`

export interface BlockField {
  key: string;
  label: string;
  kind: FieldKind;
  /** Limite de caracteres mostrado no contador do editor. */
  limit?: number;
  itemFields?: { key: string; label: string; kind: "text" | "textarea" | "list" | "media"; limit?: number }[];
}

export interface BlockDef {
  type: string;
  label: string;
  hint: string;
  fields: BlockField[];
}

export const BLOCK_DEFS: BlockDef[] = [
  {
    type: "heroi",
    label: "Herói",
    hint: "Etiqueta, título em duas linhas, lead, três CTA, pílulas e as etiquetas sobre a maqueta.",
    fields: [
      { key: "badge", label: "Etiqueta", kind: "text", limit: 40 },
      { key: "h1a", label: "Título, primeira linha", kind: "text", limit: 40 },
      { key: "h1b", label: "Título, segunda linha (a azul)", kind: "text", limit: 40 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 180 },
      { key: "cta1", label: "CTA principal", kind: "text", limit: 24 },
      { key: "cta2", label: "CTA secundário", kind: "text", limit: 24 },
      { key: "cta3", label: "CTA terciário (vai à maqueta)", kind: "text", limit: 24 },
      { key: "chips", label: "Pílulas", kind: "list", limit: 80 },
      { key: "tags", label: "Etiquetas sobre a maqueta (4)", kind: "list", limit: 24 },
    ],
  },
  {
    type: "logos",
    label: "Faixa de logos",
    hint: "Tira de logos em ciclo, com título e frase do ecossistema.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 60 },
      { key: "lead", label: "Frase", kind: "text", limit: 120 },
      {
        key: "items",
        label: "Logos",
        kind: "items",
        itemFields: [
          { key: "media_id", label: "Ficheiro", kind: "media" },
          { key: "alt", label: "Texto alternativo", kind: "text" },
          { key: "href", label: "Ligação", kind: "text" },
        ],
      },
    ],
  },
  {
    type: "recursos",
    label: "Funcionalidades",
    hint: "Cinco cartões: três em cima, e em baixo um estreito mais um largo com o painel do mapa.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 180 },
      { key: "map_title", label: "Título do painel do mapa", kind: "text", limit: 40 },
      { key: "map_note", label: "Nota do painel do mapa", kind: "textarea", limit: 140 },
      {
        key: "items",
        label: "Funcionalidades",
        kind: "items",
        itemFields: [
          { key: "title", label: "Título", kind: "text", limit: 60 },
          { key: "text", label: "Texto", kind: "textarea", limit: 220 },
          { key: "bullets", label: "Marcadores", kind: "list" },
        ],
      },
    ],
  },
  {
    type: "passos",
    label: "Começar em três passos",
    hint: "Três passos numerados, cada um com duas miniaturas, e o painel do portal por baixo.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 180 },
      { key: "panel_title", label: "Título do painel", kind: "text", limit: 60 },
      { key: "panel_text", label: "Texto do painel", kind: "textarea", limit: 220 },
      {
        key: "steps",
        label: "Passos",
        itemFields: [
          { key: "n", label: "Número", kind: "text", limit: 4 },
          { key: "title", label: "Título", kind: "text", limit: 60 },
          { key: "text", label: "Texto", kind: "textarea", limit: 220 },
          { key: "m1", label: "Miniatura 1 · título", kind: "text", limit: 30 },
          { key: "m1cta", label: "Miniatura 1 · botão", kind: "text", limit: 20 },
          { key: "m2", label: "Miniatura 2 · título", kind: "text", limit: 30 },
          { key: "m2a", label: "Miniatura 2 · linha 1", kind: "text", limit: 30 },
          { key: "m2b", label: "Miniatura 2 · linha 2", kind: "text", limit: 30 },
        ],
        kind: "items",
      },
    ],
  },
  {
    type: "porque",
    label: "Porquê BusUp",
    hint: "Números de produto: valor e rótulo.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 180 },
      {
        key: "stats",
        label: "Números",
        kind: "items",
        itemFields: [
          { key: "value", label: "Valor", kind: "text", limit: 8 },
          { key: "label", label: "Rótulo", kind: "text", limit: 60 },
        ],
      },
    ],
  },
  {
    type: "casos",
    label: "Casos",
    hint: "Depoimentos: tipo de operação, citação e atribuição.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 220 },
      {
        key: "items",
        label: "Depoimentos",
        kind: "items",
        itemFields: [
          { key: "kind", label: "Tipo", kind: "text", limit: 40 },
          { key: "quote", label: "Citação", kind: "textarea", limit: 260 },
          { key: "who", label: "Quem", kind: "text", limit: 80 },
        ],
      },
    ],
  },
  {
    type: "precos",
    label: "Preços",
    hint: "Referencia os planos geridos em Preços e planos.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 200 },
      { key: "plan_ids", label: "Planos", kind: "plans" },
      { key: "table_col", label: "Coluna da tabela", kind: "text", limit: 40 },
      { key: "table_foot", label: "Linha final da tabela", kind: "text", limit: 60 },
      { key: "quote", label: "Rótulo do pedido", kind: "text", limit: 24 },
      {
        key: "notes",
        label: "Cartões de política",
        kind: "items",
        itemFields: [
          { key: "h", label: "Título", kind: "text", limit: 60 },
          { key: "p", label: "Texto", kind: "textarea", limit: 240 },
        ],
      },
    ],
  },
  {
    type: "faq",
    label: "FAQ",
    hint: "Perguntas e respostas.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 180 },
      {
        key: "items",
        label: "Perguntas",
        kind: "items",
        itemFields: [
          { key: "q", label: "Pergunta", kind: "text", limit: 120 },
          { key: "a", label: "Resposta", kind: "textarea", limit: 400 },
        ],
      },
    ],
  },
  {
    type: "form",
    label: "Formulário",
    hint: "Pedido de contacto: campos, factos e estado de enviado.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 240 },
      { key: "facts", label: "Factos", kind: "list", limit: 80 },
      {
        key: "fields",
        label: "Campos",
        kind: "items",
        itemFields: [
          { key: "key", label: "Chave", kind: "text", limit: 24 },
          { key: "label", label: "Rótulo", kind: "text", limit: 40 },
        ],
      },
      { key: "submit", label: "Botão", kind: "text", limit: 24 },
      { key: "note", label: "Nota", kind: "text", limit: 120 },
      { key: "sent_title", label: "Título do enviado", kind: "text", limit: 40 },
      { key: "sent_text", label: "Texto do enviado", kind: "textarea", limit: 160 },
    ],
  },
  {
    type: "eco",
    label: "Ecossistema",
    hint: "Quem constrói o BusUp, com os sistemas UpDigital.",
    fields: [
      { key: "label", label: "Etiqueta", kind: "text", limit: 40 },
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 300 },
      { key: "note", label: "Nota", kind: "text", limit: 120 },
      { key: "system_ids", label: "Sistemas", kind: "systems" },
    ],
  },
  {
    type: "cta",
    label: "CTA",
    hint: "Chamada final em faixa navy, com dois botões e os factos por baixo.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 200 },
      { key: "cta1", label: "CTA principal", kind: "text", limit: 24 },
      { key: "cta2", label: "CTA secundário", kind: "text", limit: 24 },
      { key: "facts", label: "Factos", kind: "list", limit: 60 },
    ],
  },
  {
    type: "richtext",
    label: "Texto",
    hint: "HTML restrito: h2, h3, p, ul, ol, a, strong, em.",
    fields: [
      { key: "h2", label: "Título", kind: "text", limit: 80 },
      { key: "lead", label: "Lead", kind: "textarea", limit: 200 },
      { key: "html", label: "Conteúdo", kind: "richtext" },
    ],
  },
  {
    type: "media",
    label: "Media",
    hint: "Uma imagem com legenda, à largura do conteúdo ou total.",
    fields: [
      { key: "media_id", label: "Ficheiro", kind: "media" },
      { key: "caption", label: "Legenda", kind: "text", limit: 120 },
      { key: "width", label: "Largura (content ou full)", kind: "text", limit: 10 },
    ],
  },
];

export function blockDef(type: string): BlockDef {
  return BLOCK_DEFS.find((b) => b.type === type) || BLOCK_DEFS[BLOCK_DEFS.length - 2];
}

/** Conteúdo inicial de um bloco novo: todos os campos vazios nos dois idiomas. */
export function emptyContent(type: string): Record<string, unknown> {
  const def = blockDef(type);
  const out: Record<string, unknown> = {};
  for (const field of def.fields) {
    if (field.kind === "items") out[field.key] = [];
    else if (field.kind === "plans" || field.kind === "systems") out[field.key] = [];
    else if (field.kind === "list") out[field.key] = { pt: [], en: [] };
    else if (field.kind === "media") out[field.key] = null;
    else out[field.key] = { pt: "", en: "" };
  }
  return out;
}

/**
 * HTML restrito do bloco `richtext`: só as etiquetas que a especificação
 * autoriza. Tudo o resto sai — o conteúdo do CMS acaba dentro da página
 * pública, e uma etiqueta a mais aqui é um script a mais lá.
 */
const ALLOWED_TAGS = new Set(["H2", "H3", "P", "UL", "OL", "LI", "A", "STRONG", "EM", "BR"]);

export function sanitizeRichText(html: string): string {
  if (typeof window === "undefined") return "";
  const holder = document.createElement("div");
  holder.innerHTML = html;

  const walk = (node: Element) => {
    for (const child of Array.from(node.children)) {
      walk(child);
      if (!ALLOWED_TAGS.has(child.tagName)) {
        child.replaceWith(...Array.from(child.childNodes));
        continue;
      }
      for (const attr of Array.from(child.attributes)) {
        const keep =
          child.tagName === "A" &&
          attr.name === "href" &&
          /^(https?:|mailto:|\/)/i.test(attr.value.trim());
        if (!keep) child.removeAttribute(attr.name);
      }
      if (child.tagName === "A") {
        child.setAttribute("rel", "noopener noreferrer");
      }
    }
  };
  walk(holder);
  return holder.innerHTML;
}
