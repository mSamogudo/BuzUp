import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bus,
  Coins,
  Cpu,
  CreditCard,
  FileText,
  Gift,
  LayoutDashboard,
  Map,
  MapPin,
  MonitorSmartphone,
  NfcIcon,
  Palette,
  PackageCheck,
  ReceiptText,
  Route,
  Smartphone,
  Ticket,
  Truck,
  UserCheck,
  Users,
  Wallet,
} from "lucide-react";
import type { TranslationKey } from "../lib/i18n";
export type NavItem = {
  i18nKey: TranslationKey;
  path: string;
  icon: LucideIcon;
  end?: boolean;
  children?: NavItem[];
  /** Capacidades que dão acesso (basta uma). Sem `caps`, é visível a todos. */
  caps?: string[];
};
export const NAV_ITEMS: NavItem[] = [
  { i18nKey: "dashboard", path: "/app", icon: LayoutDashboard, end: true },
  { i18nKey: "routes", path: "/app/routes", icon: Route, caps: ["routes.read"] },
  { i18nKey: "stops", path: "/app/stops", icon: MapPin, caps: ["stops.read"] },
  { i18nKey: "vehicles", path: "/app/vehicles", icon: Truck, caps: ["vehicles.read"] },
  { i18nKey: "drivers", path: "/app/drivers", icon: UserCheck, caps: ["drivers.read"] },
  { i18nKey: "trips", path: "/app/trips", icon: Bus, caps: ["trips.read"] },
  { i18nKey: "fares", path: "/app/fares", icon: Ticket, caps: ["fares.read"] },
  { i18nKey: "packages", path: "/app/packages", icon: Gift, caps: ["packages.read"] },
  { i18nKey: "passengers", path: "/app/passengers", icon: Users, caps: ["passengers.read"] },
  { i18nKey: "wallets", path: "/app/wallets", icon: Wallet, caps: ["wallets.read"] },
  { i18nKey: "cards", path: "/app/cards", icon: NfcIcon, caps: ["cards.read"], children: [
    { i18nKey: "physicalCards", path: "/app/cards/physical", icon: NfcIcon, caps: ["cards.read"] },
    { i18nKey: "digitalCards", path: "/app/cards/digital", icon: Smartphone, caps: ["cards.read"] },
  ]},
  { i18nKey: "financial", path: "/app/financial", icon: CreditCard, caps: ["payments.read"] },
  { i18nKey: "guestCheckouts", path: "/app/guest-checkouts", icon: ReceiptText, caps: ["payments.read"] },
  { i18nKey: "devices", path: "/app/devices", icon: Cpu, caps: ["devices.read"] },
  { i18nKey: "posSessions", path: "/app/pos-sessions", icon: MonitorSmartphone, caps: ["devices.read"] },
  { i18nKey: "map", path: "/app/map", icon: Map, caps: ["devices.read"] },
  { i18nKey: "releases", path: "/app/releases", icon: PackageCheck, caps: ["devices.manage"] },
  { i18nKey: "users", path: "/app/users", icon: Users, caps: ["users.read"] },
  { i18nKey: "agentRevenue", path: "/app/agent-revenue", icon: Coins, caps: ["reports.read"] },
  { i18nKey: "reports", path: "/app/reports", icon: BarChart3, caps: ["reports.read"] },
  { i18nKey: "audit", path: "/app/audit", icon: FileText, caps: ["audit.read"] },
  { i18nKey: "branding", path: "/app/branding", icon: Palette, caps: ["settings.manage"] },
];
/** Itens visíveis para o utilizador: superuser vê tudo; senão basta uma capability. */
export function visibleNavItems(items: NavItem[], caps: string[], isSuperuser: boolean): NavItem[] {
  if (isSuperuser) return items;
  const allowed = new Set(caps);
  return items
    .filter((it) => !it.caps || it.caps.some((c) => allowed.has(c)))
    .map((it) => it.children
      ? { ...it, children: it.children.filter((ch) => !ch.caps || ch.caps.some((c) => allowed.has(c))) }
      : it);
}
