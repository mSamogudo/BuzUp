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
  NfcIcon,
  Palette,
  PackageCheck,
  Route,
  ShieldCheck,
  Smartphone,
  Ticket,
  Truck,
  UserCheck,
  Users,
} from "lucide-react";
import type { TranslationKey } from "../lib/i18n";

export type NavItem = {
  i18nKey: TranslationKey;
  path: string;
  icon: LucideIcon;
  end?: boolean;
  children?: NavItem[];
};

export const NAV_ITEMS: NavItem[] = [
  { i18nKey: "dashboard", path: "/app", icon: LayoutDashboard, end: true },
  { i18nKey: "routes", path: "/app/routes", icon: Route },
  { i18nKey: "stops", path: "/app/stops", icon: MapPin },
  { i18nKey: "vehicles", path: "/app/vehicles", icon: Truck },
  { i18nKey: "drivers", path: "/app/drivers", icon: UserCheck },
  { i18nKey: "trips", path: "/app/trips", icon: Bus },
  { i18nKey: "fares", path: "/app/fares", icon: Ticket },
  { i18nKey: "packages", path: "/app/packages", icon: Gift },
  { i18nKey: "passengers", path: "/app/passengers", icon: Users },
  { i18nKey: "cards", path: "/app/cards", icon: NfcIcon, children: [
    { i18nKey: "physicalCards", path: "/app/cards/physical", icon: NfcIcon },
    { i18nKey: "digitalCards", path: "/app/cards/digital", icon: Smartphone },
  ]},
  { i18nKey: "financial", path: "/app/financial", icon: CreditCard },
  { i18nKey: "devices", path: "/app/devices", icon: Cpu },
  { i18nKey: "map", path: "/app/map", icon: Map },
  { i18nKey: "releases", path: "/app/releases", icon: PackageCheck },
  { i18nKey: "users", path: "/app/users", icon: Users },
  { i18nKey: "agentRevenue", path: "/app/agent-revenue", icon: Coins },
  { i18nKey: "reports", path: "/app/reports", icon: BarChart3 },
  { i18nKey: "audit", path: "/app/audit", icon: FileText },
  { i18nKey: "branding", path: "/app/branding", icon: Palette },
];
