import type { CSSProperties } from "react";
import { LOGO_CLARO, LOGO_ESCURO } from "./BusUpChrome";
import { ALTURA_BUSUP, LOGOS_ECO } from "./logos-ecossistema";

/* A faixa dos produtos da UpDigital — a mesma nas três páginas.
 *
 * SUBSTITUI A FITA QUE DESLIZAVA E AS GRELHAS SOLTAS. A fita punha os
 * logótipos em pílulas de 62px a 26px de altura, todos iguais, a correr sem
 * parar; nas grelhas cada página tinha a sua cópia do mesmo markup. Aqui cada
 * logótipo tem uma célula do mesmo tamanho, a altura óptica que vem do
 * ficheiro de dados, e a tinta certa para o tema. Nada se mexe.
 *
 * O BUSUP VAI PRIMEIRO E MARCADO, não recolorido: um traço azul em cima da
 * célula e `aria-current`, que o leitor de ecrã anuncia. Não leva ligação —
 * abria a própria página noutro separador.
 *
 * `fluida` é a variante da secção "Quem constrói": duas colunas que enchem a
 * metade da grelha, em vez das quatro células fixas da faixa larga.
 */

type Props = { fluida?: boolean };

function altura(px: number) {
  return { "--logo-h": `${px}px` } as CSSProperties;
}

export default function FaixaLogotipos({ fluida = false }: Props) {
  return (
    <ul className={`bzc-produtos${fluida ? " bzc-produtos--fluida" : ""}`}>
      <li>
        <span aria-current="page" className="bzc-produto" style={altura(ALTURA_BUSUP)}>
          <img alt="BusUp" data-logo="light" src={LOGO_CLARO} />
          <img alt="BusUp" data-logo="dark" src={LOGO_ESCURO} />
        </span>
      </li>
      {LOGOS_ECO.map((l) => (
        <li key={l.nome}>
          <a
            className="bzc-produto"
            data-placa={l.placaClara ? "clara" : undefined}
            href={l.url}
            rel="noopener"
            style={altura(l.altura)}
            target="_blank"
          >
            <img alt={l.nome} data-logo="light" src={l.claro} />
            <img alt={l.nome} data-logo="dark" src={l.escuro} />
          </a>
        </li>
      ))}
    </ul>
  );
}
