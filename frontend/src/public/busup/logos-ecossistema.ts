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
 *
 * A ALTURA É ÓPTICA, NÃO IGUAL. Com todos a 26px o CashUp (4,1:1) parecia
 * maior do que o GoUp (2,8:1) e o brasão da OSSOMA ficava um selo de 26px.
 * Cada altura sai da caixa de tinta MEDIDA de cada ficheiro — sem a margem
 * transparente — para que a tinta ocupe mais ou menos a mesma área:
 * `tinta ≈ 30px × √(3,5 / proporção)`, e depois soma-se a margem do ficheiro.
 * O BusUp tem 10% de margem em cima e em baixo, por isso leva mais.
 */

export type LogoEco = {
  nome: string;
  /** Tinta escura — vai sobre fundo claro. */
  claro: string;
  /** Tinta clara — vai sobre fundo escuro. */
  escuro: string;
  url: string;
  /** Altura do ficheiro, em px, na faixa de secretária. No telemóvel encolhe. */
  altura: number;
  /** A arte não lê sobre navy, nem na variante escura: no tema escuro a
   *  célula fica clara e mostra o ficheiro `claro`. */
  placaClara?: boolean;
};

const BASE = "/ecosystem/logos";

export const LOGOS_ECO: LogoEco[] = [
  { nome: "PayUp", claro: `${BASE}/payup-light.webp`, escuro: `${BASE}/payup-dark.webp`, url: "https://payup.updigital.co.mz", altura: 32 },
  { nome: "CashUp", claro: `${BASE}/cashup-light.webp`, escuro: `${BASE}/cashup-dark.webp`, url: "https://cashup.updigital.co.mz", altura: 30 },
  { nome: "GateUp", claro: `${BASE}/gateup-light.webp`, escuro: `${BASE}/gateup-dark.webp`, url: "https://gateup.updigital.co.mz", altura: 30 },
  { nome: "GoUp", claro: `${BASE}/goup-light.png`, escuro: `${BASE}/goup-dark.png`, url: "https://goup.updigital.co.mz", altura: 35, placaClara: true },
  { nome: "Vura", claro: `${BASE}/vura-light.webp`, escuro: `${BASE}/vura-dark.png`, url: "https://vura.updigital.co.mz", altura: 32 },
  /* O TaxUp não vinha no protótipo — o logótipo chegou depois, com os outros.
     O endereço abaixo segue o padrão dos cinco irmãos e NÃO foi confirmado. */
  { nome: "TaxUp", claro: `${BASE}/taxup-light.webp`, escuro: `${BASE}/taxup-dark.webp`, url: "https://taxup.updigital.co.mz", altura: 32 },
  { nome: "Ossoma", claro: `${BASE}/ossoma-cor.webp`, escuro: `${BASE}/ossoma-cor.webp`, url: "https://ossoma.updigital.co.mz", altura: 58, placaClara: true },
];

/** O BusUp na faixa: é o produto desta página, por isso não leva ligação. */
export const ALTURA_BUSUP = 40;
