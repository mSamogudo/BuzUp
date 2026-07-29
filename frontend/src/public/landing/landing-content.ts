/** Conteúdo e receitas de classe da landing.
 *
 * Padrão herdado das landings irmãs (VURA/Keeper): as constantes de classe
 * garantem que o ritmo vertical, os gutters e os CTAs não divergem entre
 * secções — muda-se num sítio, muda em toda a página.
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

export const NAV = [
  { id: "produto", label: "Produto" },
  { id: "como-funciona", label: "Como funciona" },
  { id: "solucoes", label: "Soluções" },
  { id: "plataforma", label: "Plataforma" },
  { id: "ecossistema", label: "Ecossistema" },
];

export const STATS = [
  { v: "3", l: "canais de venda e validação" },
  { v: "2", l: "carteiras móveis integradas" },
  { v: "100%", l: "da receita registada" },
  { v: "0", l: "obras na frota actual" },
];

export const HOW_STEPS = [
  {
    title: "Publique as suas partidas",
    text: "Rotas, horários e frota no portal. As partidas ficam à venda com lugares e preço por troço.",
  },
  {
    title: "O passageiro compra",
    text: "No site ou na app: escolhe data, lugar no autocarro e paga por M-Pesa ou e-Mola. Recebe o bilhete em PDF com QR.",
  },
  {
    title: "Ou paga a bordo",
    text: "Sem smartphone? O agente vende no terminal POS e o passageiro usa cartão NFC recarregável.",
  },
  {
    title: "Embarque validado",
    text: "O agente lê o QR ou aproxima o cartão. Um bilhete, uma viagem — sem reutilização.",
  },
  {
    title: "Viagem em curso",
    text: "O motorista inicia a viagem no terminal e o autocarro passa a aparecer no mapa em tempo real.",
  },
  {
    title: "Contas fechadas",
    text: "Receita por rota, viagem e agente, com fecho de caixa e relatórios prontos a exportar.",
  },
];

export const MODULES = [
  { icon: QrCode, title: "Bilhete digital", text: "QR no telemóvel ou impresso, com código curto para leitura manual." },
  { icon: NfcIcon, title: "Cartão NFC", text: "Cartão recarregável para quem não tem smartphone. Ninguém fica de fora." },
  { icon: Wallet, title: "Carteira e recargas", text: "Saldo em Meticais, carregado por M-Pesa, e-Mola ou num agente." },
  { icon: Ticket, title: "Venda antecipada", text: "Bilhetes para dias seguintes, com lugar marcado e lotação controlada." },
  { icon: MapPin, title: "Frota no mapa", text: "Posição real dos autocarros em viagem, visível ao passageiro." },
  { icon: BarChart3, title: "Receita e relatórios", text: "Por rota, viagem, agente e método de pagamento. Exportável." },
  { icon: RouteIcon, title: "Rotas e horários", text: "Paragens, troços e horários recorrentes que geram as partidas do dia." },
  { icon: ShieldCheck, title: "Auditoria", text: "Cada venda e validação com registo. A receita deixa de depender de confiança." },
  { icon: ArrowRightLeft, title: "Preço por troço", text: "Tarifa entre paragens, do bairro à viagem internacional." },
];

export const PLATFORM_PILLS = [
  "Painel de receita", "Rotas e paragens", "Horários", "Frota e livrete", "Motoristas",
  "Agentes e terminais", "Passageiros", "Cartões", "Tarifas e pacotes", "Bilhetes ocasionais",
  "Fecho de caixa", "Relatórios", "Auditoria", "Actualização das apps",
];

export const SECURITY_POINTS = [
  "Cada bilhete tem QR assinado e código curto — não se reutiliza nem se falsifica.",
  "Dinheiro deixa de passar de mão em mão: a receita é registada na origem.",
  "Perfis e permissões por função: cada pessoa vê apenas o que lhe compete.",
  "Registo de auditoria de vendas, validações e alterações de configuração.",
  "Pagamentos pelas carteiras nacionais, sem guardar dados de cartão.",
  "Funciona com ligação instável: o terminal opera e sincroniza depois.",
];

export const AUDIENCES = [
  {
    icon: Bus,
    name: "Operadores de transporte",
    text: "Urbano, interurbano e internacional. Venda antecipada com lugar marcado, controlo de lotação e receita rastreada por viagem.",
  },
  {
    icon: Building2,
    name: "Empresas",
    text: "Transporte de colaboradores com passes mensais, controlo de acesso ao autocarro e relatórios de utilização por departamento.",
  },
  {
    icon: GraduationCap,
    name: "Escolas e instituições",
    text: "Passes de estudante, embarque validado por cartão e histórico de viagens para as famílias e para a direcção.",
  },
  {
    icon: Users,
    name: "Passageiros",
    text: "Compram no telemóvel, pagam com a carteira que já usam e seguem o autocarro no mapa até à paragem.",
  },
];

export const TOOLS = [
  {
    icon: Smartphone, name: "App Passageiro", tag: "Android",
    items: ["Carteira em Meticais", "Recarga M-Pesa e e-Mola", "Bilhete por QR Code", "Mapa da frota em tempo real"],
  },
  {
    icon: Store, name: "App POS", tag: "Agente e motorista",
    items: ["Venda e validação a bordo", "Leitura QR e cartão NFC", "Início e fecho de viagens", "Terminais SUNMI e Urovo"],
  },
  {
    icon: Gauge, name: "Portal de Gestão", tag: "Operação e direcção",
    items: ["Rotas, horários e frota", "Receita e reconciliação", "Relatórios exportáveis", "Auditoria e permissões"],
  },
];

export const ECOSYSTEM = [
  { name: "PayUp", text: "Pagamentos e carteiras móveis" },
  { name: "CashUp", text: "Gestão de caixa e tesouraria" },
  { name: "TaxUp", text: "Mobilidade e táxis" },
  { name: "GateUp", text: "Controlo de acessos" },
  { name: "GoUp", text: "Transporte corporativo" },
];

export const BENEFITS = [
  { icon: Banknote, title: "Fim do dinheiro na mão", text: "Sem troco nem notas a circular. Menos furtos, menos erros e mais higiene a bordo." },
  { icon: TrendingUp, title: "Receita rastreável", text: "Cada bilhete fica registado. Combate directo à evasão de receita e ao desvio de fundos." },
  { icon: BarChart3, title: "Dados para decidir", text: "Fluxo de passageiros por rota, horário e viatura — informação real para planear." },
  { icon: CreditCard, title: "Todos os meios", text: "Carteira digital, cartão NFC ou dinheiro no agente. O passageiro escolhe." },
];
