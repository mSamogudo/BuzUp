/** Ícones e constantes da landing.
 *
 * O TEXTO vive em landing-copy.ts (PT/EN) — aqui ficam só os ícones, por
 * posição, e os dados de contacto, que não se traduzem.
 */

import {
  ArrowRightLeft, BarChart3, Banknote, Bus, Building2, CreditCard, Gauge,
  GraduationCap, MapPin, NfcIcon, QrCode, Route as RouteIcon, ShieldCheck,
  Smartphone, Store, Ticket, TrendingUp, Users, Wallet,
} from "lucide-react";

export const SALES_EMAIL = "sales@updigital.co.mz";
export const SALES_PHONE = "+258 86 693 0017";
export const SALES_PHONE_HREF = "+258866930017";
export const ADDRESS = "Av. Alberto Massavanhane, nº 1265 · Matola · Moçambique";

/** Ícones por posição — a ordem acompanha a de landing-copy.ts. */
export const BENEFIT_ICONS = [Banknote, TrendingUp, BarChart3, CreditCard];

export const MODULE_ICONS = [
  QrCode, NfcIcon, Wallet, Ticket, MapPin, BarChart3, RouteIcon, ShieldCheck, ArrowRightLeft,
];

export const AUDIENCE_ICONS = [Bus, Building2, GraduationCap, Users];

export const TOOL_ICONS = [Smartphone, Store, Gauge];
