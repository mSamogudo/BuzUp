/** Os logótipos dos produtos da UpDigital, em par: um para cada tema.
 *
 * PORQUE É QUE ISTO EXISTE. Os ficheiros que estavam em `/ecosystem/logos/`
 * eram TODOS a variante de tinta clara — feita para assentar sobre escuro.
 * Sobre os cartões brancos desta página metade de cada logótipo desaparecia:
 * via-se o "Up" a vermelho e o "Cash" não. Cada produto passa a ter os dois
 * ficheiros, e o CSS escolhe pelo tema, como já faz com o logótipo do BusUp.
 *
 * A OSSOMA tem um brasão a cores e não um logótipo de duas tintas: serve os
 * dois temas com o mesmo ficheiro.
 */

export type LogoEco = {
  nome: string;
  /** Tinta escura — vai sobre fundo claro. */
  claro: string;
  /** Tinta clara — vai sobre fundo escuro. */
  escuro: string;
  url: string;
};

const BASE = "/ecosystem/logos";

export const LOGOS_ECO: LogoEco[] = [
  { nome: "PayUp", claro: `${BASE}/payup-light.webp`, escuro: `${BASE}/payup-dark.webp`, url: "https://payup.updigital.co.mz" },
  { nome: "CashUp", claro: `${BASE}/cashup-light.webp`, escuro: `${BASE}/cashup-dark.webp`, url: "https://cashup.updigital.co.mz" },
  { nome: "GateUp", claro: `${BASE}/gateup-light.webp`, escuro: `${BASE}/gateup-dark.webp`, url: "https://gateup.updigital.co.mz" },
  { nome: "GoUp", claro: `${BASE}/goup-light.png`, escuro: `${BASE}/goup-dark.png`, url: "https://goup.updigital.co.mz" },
  { nome: "Vura", claro: `${BASE}/vura-light.webp`, escuro: `${BASE}/vura-dark.png`, url: "https://vura.updigital.co.mz" },
  /* O TaxUp não vinha no protótipo — o logótipo chegou depois, com os outros.
     O endereço abaixo segue o padrão dos cinco irmãos e NÃO foi confirmado. */
  { nome: "TaxUp", claro: `${BASE}/taxup-light.webp`, escuro: `${BASE}/taxup-dark.webp`, url: "https://taxup.updigital.co.mz" },
  { nome: "Ossoma", claro: `${BASE}/ossoma-cor.webp`, escuro: `${BASE}/ossoma-cor.webp`, url: "https://ossoma.updigital.co.mz" },
];
