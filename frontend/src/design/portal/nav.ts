/**
 * Navegação do portal, agrupada por domínio.
 *
 * Estrutura e rótulos portados do objecto `NAV` de
 * docs/design-handoff/design/Portal BusUp v2.dc.html (inventário A0.2).
 * Os ícones são os traçados SVG do desenho — não se usa uma biblioteca de
 * ícones aqui, para o vocabulário visual ficar exactamente o do handoff.
 */

/** Traçados SVG (viewBox 0 0 24 24, stroke currentColor) do desenho. */
export const NAV_ICON: Record<string, string> = {
  painel: "M4 19V5m5 14V9m5 10V4m5 15v-7",
  rotas: "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Zm0-13.2a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4Z",
  paragens: "M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Zm0-13.2a2.2 2.2 0 1 1 0 4.4 2.2 2.2 0 0 1 0-4.4Z",
  veiculos: "M4 17V9a2 2 0 0 1 2-2h7l4 4v6M4 17h16M7 17v2m10-2v2M6 11h6",
  motoristas: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8m-7 8a7 7 0 0 1 14 0M9 16h6",
  viagens: "M4 16V7a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3v9M4 16h16M4 16v3h3v-3m10 0v3h3v-3M8 8h8M7 12h2m6 0h2",
  mapa: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14",
  tarifas: "M4 7h11l5 5-5 5H4zM8 12h.01",
  pacotes: "M4 8h16v12H4zM4 8l2-4h12l2 4M12 4v16",
  passageiros: "M4 6h16v12H4zM4 10h16M7 14h5M16 14h1",
  carteiras: "M4 8h13a3 3 0 0 1 3 3v5a2 2 0 0 1-2 2H5a1 1 0 0 1-1-1zM4 8V6a1 1 0 0 1 1-1h10M16 13h2",
  cartoes_fisicos: "M3 7h18v11H3zM3 11h18M7 15h4",
  cartoes_digitais: "M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1m2 15h4",
  financeiro: "M3 7h18v11H3zM3 11h18M7 15h4",
  ocasionais: "M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2 2 2 0 0 0 0 4 2 2 0 0 0 0 4 2 2 0 0 1-2 2H6a2 2 0 0 1-2-2 2 2 0 0 0 0-4 2 2 0 0 0 0-4M12 8v8",
  pos: "M7 4h10a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1m2 4h6m-6 4h6m-6 4h3",
  receita: "M12 3v18M8 7h6a3 3 0 0 1 0 6h-4a3 3 0 0 0 0 6h6",
  relatorios: "M6 3h9l4 4v14H6zM14 3v4h4M9 13h6M9 17h4",
  terminais: "M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1m2 15h4",
  apks: "M12 3v12m-4-4 4 4 4-4M5 19h14",
  utilizadores: "M12 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7m-6 9a6 6 0 0 1 12 0M18 8l2 2 3-3",
  auditoria: "M12 3l7 3v6c0 4-3 7.4-7 9-4-1.6-7-5-7-9V6zM9 12l2 2 4-4",
  marca: "M4 6h16v12H4zM8 10h8M8 14h5",
  termos: "M6 3h9l4 4v14H6zM14 3v4h4M9 12h6M9 16h4",
  perfil: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M5.4 15.6l-1.7 1a8.4 8.4 0 0 1 0-9.2l1.7 1M18.6 8.4l1.7-1a8.4 8.4 0 0 1 0 9.2l-1.7-1",
  agentes: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8m-7 8a7 7 0 0 1 14 0M9 16h6",
  paginas: "M6 3h8l4 4v14H6zM14 3v4h4",
  editor: "M4 20h4l10-10-4-4L4 16zM14 6l4 4",
  media: "M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5M9 9.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z",
  menus: "M4 6h16M4 12h16M4 18h10",
  seo: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM20 20l-4-4",
  planos: "M12 3v18M8 7h6a3 3 0 0 1 0 6h-4a3 3 0 0 0 0 6h6",
  eco: "M5 8a3 3 0 1 0 0-.001M19 8a3 3 0 1 0 0-.001M12 20a3 3 0 1 0 0-.001M7 9.5 11 17m6-7.5L13 17",
  pedidos: "M4 6h16v12H4zM4 7l8 6 8-6",
  agenda: "M4 6h16v14H4zM4 10h16M9 3v4m6-4v4",
  versoes: "M4 12a8 8 0 1 0 3-6.2M4 4v4h4M12 8v4l3 2",
  cms_users: "M4 20a6 6 0 0 1 12 0M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8m8 9a5 5 0 0 0-4-4.9M16 5.2a3.5 3.5 0 0 1 0 6.6",
};

/** Sigla de duas letras, usada nas migalhas e nos cartões sem ícone. */
export const NAV_CODE: Record<string, string> = {
  painel: "PN", rotas: "RT", paragens: "PR", veiculos: "VC", motoristas: "MT",
  viagens: "VG", mapa: "MP", tarifas: "TF", pacotes: "PC", passageiros: "PA",
  carteiras: "CT", cartoes_fisicos: "CF", cartoes_digitais: "CD", financeiro: "PG",
  ocasionais: "BO", pos: "PS", receita: "RA", relatorios: "RL", terminais: "TM",
  apks: "AK", utilizadores: "UZ", auditoria: "AU", marca: "MC", termos: "TC",
  perfil: "DF", agentes: "AT", paginas: "PÁ", editor: "ED", media: "MD",
  menus: "MN", seo: "SE", planos: "PL", eco: "EC", pedidos: "PD", agenda: "AG",
  versoes: "VS", cms_users: "UT",
};

export type NavEntry = {
  /** Chave do desenho — liga ícone, sigla, papéis e migalhas. */
  key: string;
  label: string;
  path: string;
  /** Rota exacta (o Painel é `/app`, que prefixa tudo o resto). */
  end?: boolean;
  /** Capacidades da API que dão acesso; basta uma. Sem `caps`, é livre. */
  caps?: string[];
  /** Módulo desenhado como proposta: abre com aviso de que não há backend. */
  proposal?: boolean;
};

export type NavGroup = { label: string; items: NavEntry[] };

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "",
    items: [{ key: "painel", label: "Painel", path: "/app", end: true }],
  },
  {
    label: "Transporte",
    items: [
      { key: "rotas", label: "Rotas", path: "/app/routes", caps: ["routes.read"] },
      { key: "paragens", label: "Paragens", path: "/app/stops", caps: ["stops.read"] },
      { key: "veiculos", label: "Veículos", path: "/app/vehicles", caps: ["vehicles.read"] },
      { key: "motoristas", label: "Motoristas", path: "/app/drivers", caps: ["drivers.read"] },
    ],
  },
  {
    label: "Operação",
    items: [
      { key: "viagens", label: "Viagens", path: "/app/trips", caps: ["trips.read"] },
      { key: "mapa", label: "Mapa", path: "/app/map", caps: ["devices.read"] },
    ],
  },
  {
    label: "Tarifação",
    items: [
      { key: "tarifas", label: "Tarifas", path: "/app/fares", caps: ["fares.read"] },
      { key: "pacotes", label: "Pacotes", path: "/app/packages", caps: ["packages.read"] },
    ],
  },
  {
    label: "Passageiros",
    items: [
      { key: "passageiros", label: "Passageiros", path: "/app/passengers", caps: ["passengers.read"] },
      { key: "carteiras", label: "Carteiras", path: "/app/wallets", caps: ["wallets.read"] },
      { key: "cartoes_fisicos", label: "Cartões Físicos", path: "/app/cards/physical", caps: ["cards.read"] },
      { key: "cartoes_digitais", label: "Carteiras Digitais", path: "/app/cards/digital", caps: ["cards.read"] },
    ],
  },
  {
    label: "Financeiro",
    items: [
      { key: "financeiro", label: "Pagamentos", path: "/app/financial", caps: ["payments.read"] },
      { key: "ocasionais", label: "Bilhetes Ocasionais", path: "/app/guest-checkouts", caps: ["payments.read"] },
      { key: "pos", label: "Sessões POS", path: "/app/pos-sessions", caps: ["devices.read"] },
      { key: "receita", label: "Receita de Agentes", path: "/app/agent-revenue", caps: ["reports.read"] },
      { key: "relatorios", label: "Relatórios", path: "/app/reports", caps: ["reports.read"] },
    ],
  },
  {
    label: "Sistema",
    items: [
      { key: "terminais", label: "Terminais", path: "/app/devices", caps: ["devices.read"] },
      { key: "apks", label: "APKs", path: "/app/releases", caps: ["devices.manage"] },
      { key: "utilizadores", label: "Utilizadores", path: "/app/users", caps: ["users.read"] },
      { key: "auditoria", label: "Auditoria", path: "/app/audit", caps: ["audit.read"] },
      { key: "marca", label: "Marca", path: "/app/branding", caps: ["settings.manage"] },
      { key: "termos", label: "Termos e Condições", path: "/app/terms", caps: ["settings.manage"] },
      { key: "perfil", label: "Definições", path: "/app/settings" },
    ],
  },
  {
    label: "Conteúdo",
    items: [
      { key: "paginas", label: "Páginas do site", path: "/app/cms/pages", caps: ["content.read"] },
      { key: "media", label: "Media", path: "/app/cms/media", caps: ["media.manage", "content.read"] },
      { key: "menus", label: "Menus e rodapé", path: "/app/cms/menus", caps: ["menus.manage", "content.read"] },
      { key: "seo", label: "SEO e partilha", path: "/app/cms/seo", caps: ["seo.manage", "content.read"] },
      { key: "planos", label: "Preços e planos", path: "/app/cms/plans", caps: ["plans.manage", "content.read"] },
      { key: "eco", label: "Ecossistema", path: "/app/cms/eco-systems", caps: ["content.read"] },
      { key: "pedidos", label: "Pedidos", path: "/app/cms/requests", caps: ["requests.read", "content.read"] },
      { key: "agenda", label: "Agendamento", path: "/app/cms/schedules", caps: ["content.publish", "content.read"] },
      { key: "versoes", label: "Versões", path: "/app/cms/versions", caps: ["content.read"] },
      { key: "cms_users", label: "Utilizadores do CMS", path: "/app/cms/users", caps: ["content.read"] },
    ],
  },
  {
    label: "Propostas",
    items: [{ key: "agentes", label: "Agentes e turnos", path: "/app/shifts", proposal: true }],
  },
];

/** Separadores por módulo (MODTABS do desenho). */
export const MODULE_TABS: Record<string, [key: string, label: string][]> = {
  viagens: [["trips", "Viagens"], ["schedules", "Programações"], ["scheduler", "Agendador"]],
  tarifas: [
    ["matrix", "Tabela de preços"],
    ["fare_rules", "Regras de tarifa"],
    ["fare_products", "Produtos"],
    ["admin_fees", "Taxas administrativas"],
    ["exchange_rates", "Câmbio"],
  ],
  pacotes: [["packages", "Pacotes"], ["passenger_packages", "Subscrições"]],
  carteiras: [["wallets", "Carteiras"], ["wallet_transactions", "Movimentos"]],
  financeiro: [["payment_intents", "Pagamentos"], ["topups", "Recargas"], ["validations", "Validações"]],
  relatorios: [["reports", "Catálogo"], ["reconciliation", "Reconciliação"], ["imports", "Importações"]],
  utilizadores: [["users", "Utilizadores"], ["roles", "Roles"]],
  agentes: [["agents", "Agentes"], ["shifts", "Turnos"], ["day_closes", "Fechos de dia"]],
};

/** Oito papéis do desenho (02-tokens-e-padroes.md §9). `"*"` é acesso total. */
export type RoleDef = { key: string; label: string; modules: "*" | string[]; caps: string };

export const ROLES: RoleDef[] = [
  { key: "admin", label: "Administração", modules: "*", caps: "todas as capacidades" },
  {
    key: "ops",
    label: "Operações",
    modules: [
      "painel", "rotas", "paragens", "veiculos", "motoristas", "viagens",
      "passageiros", "cartoes_fisicos", "cartoes_digitais", "terminais", "mapa", "perfil",
    ],
    caps: "routes.read, stops.read, vehicles.read, drivers.read, trips.read, devices.read",
  },
  {
    key: "fin",
    label: "Financeiro",
    modules: [
      "painel", "tarifas", "pacotes", "carteiras", "financeiro", "ocasionais",
      "pos", "receita", "relatorios", "perfil",
    ],
    caps: "fares.read, packages.read, wallets.read, payments.read, reports.read",
  },
  {
    key: "agente",
    label: "Agente",
    modules: ["painel", "viagens", "passageiros", "cartoes_fisicos", "cartoes_digitais", "ocasionais", "perfil"],
    caps: "trips.read, passengers.read, cards.read",
  },
  {
    key: "motorista",
    label: "Motorista",
    modules: ["viagens", "perfil"],
    caps: "trips.read e actividade de viagem",
  },
  {
    key: "suporte",
    label: "Suporte",
    modules: ["passageiros", "carteiras", "cartoes_fisicos", "cartoes_digitais", "ocasionais", "perfil"],
    caps: "passengers.read, wallets.read, cards.read",
  },
  {
    key: "auditor",
    label: "Auditor",
    modules: ["painel", "auditoria", "relatorios", "perfil"],
    caps: "audit.read e reports.read",
  },
  {
    key: "conteudo",
    label: "Gestor de conteúdo",
    modules: [
      "marca", "termos", "paginas", "editor", "media", "menus", "seo",
      "planos", "eco", "pedidos", "agenda", "versoes", "cms_users", "perfil",
    ],
    caps: "settings.manage e conteúdo do site",
  },
];

export const ALL_NAV_ITEMS: NavEntry[] = NAV_GROUPS.flatMap((g) => g.items);

export function navEntryByKey(key: string): NavEntry | undefined {
  return ALL_NAV_ITEMS.find((i) => i.key === key);
}

/** Domínio a que um módulo pertence — primeira parte das migalhas. */
export function navDomain(key: string): string {
  const group = NAV_GROUPS.find((g) => g.items.some((i) => i.key === key));
  return group?.label || "Portal";
}

/**
 * Navegação visível: filtra pelas capacidades reais da conta e, quando um papel
 * está seleccionado no cabeçalho, também pelos módulos desse papel.
 */
export function visibleGroups(opts: {
  caps: string[];
  isSuperuser: boolean;
  role?: string | null;
}): NavGroup[] {
  const allowed = new Set(opts.caps);
  const roleDef = opts.role ? ROLES.find((r) => r.key === opts.role) : undefined;
  const roleModules = roleDef && roleDef.modules !== "*" ? new Set(roleDef.modules) : null;

  return NAV_GROUPS.map((group) => ({
    label: group.label,
    items: group.items.filter((item) => {
      if (roleModules && !roleModules.has(item.key)) return false;
      if (opts.isSuperuser) return true;
      if (!item.caps) return true;
      return item.caps.some((c) => allowed.has(c));
    }),
  })).filter((group) => group.items.length > 0);
}
