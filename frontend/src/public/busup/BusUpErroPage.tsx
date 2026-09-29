import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useLandingPrefs } from "../landing/useLandingPrefs";
import {
  BotaoTema, Logotipo, LogotipoUpDigital, EMAIL_VENDAS, useBusUpMeta,
} from "./BusUpChrome";
import { copyErros, erro as lerErro, type ChaveErro } from "./busup-erros-copy";
import "./busup.css";

/* Os ecrãs de erro do desenho "Ceu" — `Erros BusUp.dc.html`.
 *
 * NÃO LEVAM A CASCA DO SITE. Um 500 com a navegação completa por cima convida
 * a clicar em tudo menos no que resolve o problema; o desenho põe aqui só a
 * marca, o tema, a ajuda e o estado dos serviços. É também o que faz sentido
 * quando o erro vem do portal, que tem outra navegação.
 *
 * A REFERÊNCIA TÉCNICA DO PROTÓTIPO É UMA AMOSTRA. Escrever "/rota-antiga"
 * num 404 real seria mentir ao suporte: o que se mostra é o caminho que a
 * pessoa abriu e a hora a que o abriu. O resto — o número do incidente, o id
 * da sessão — só o servidor sabe, e entra por `referencia` quando existe.
 */

export type PropsErro = {
  chave?: ChaveErro;
  /** A cauda da referência, quando quem chama a sabe: `incidente INC-...`. */
  referencia?: string;
};

/* NÃO HÁ PÁGINA DE ESTADO DOS SERVIÇOS neste sistema. O desenho conta com uma
   — no cabeçalho e no primeiro botão do 503 — mas nenhuma rota a serve, e
   mandar "Estado dos serviços" para o formulário de contacto seria prometer o
   que não se entrega. Fica vazia: o cabeçalho salta a pílula e o 503 repete a
   tentativa. Quando a página existir, basta escrevê-la aqui. */
const ESTADO_URL = "";

const CTA_DESTINO: Record<ChaveErro, { um: string; dois: string }> = {
  "404": { um: "/", dois: "/comprar" },
  "401": { um: "/login", dois: "/" },
  "403": { um: "/app", dois: "/contactos" },
  "500": { um: "", dois: "/contactos" },   // "" = repetir, não navegar
  "503": { um: ESTADO_URL, dois: "/contactos" },
  offline: { um: "", dois: "" },
};

/** A hora no formato que o desenho usa: `04 Ago 2026, 10:12`. */
function agora(lang: "pt" | "en") {
  const d = new Date();
  const meses = lang === "en"
    ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    : ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${dd} ${meses[d.getMonth()]} ${d.getFullYear()}, ${hh}:${mm}`;
}

export default function BusUpErroPage({ chave = "404", referencia }: PropsErro) {
  const { effectiveTheme, lang } = useLandingPrefs();
  const { pathname } = useLocation();
  const t = copyErros(lang);
  const e = lerErro(lang, chave);
  const destino = CTA_DESTINO[chave];

  useBusUpMeta(`${e.pilula} · BusUp`, e.lead);

  const ref = [
    e.ref,
    chave === "404" ? pathname : null,
    referencia ?? null,
    chave === "404" || chave === "401" ? agora(lang) : null,
  ].filter(Boolean).join(" · ");

  return (
    <div className="bzc bzc-erro" data-theme={effectiveTheme} data-tom={e.tom}>
      <header className="bzc-erro-topo">
        <Link aria-label="BusUp" to="/"><Logotipo alt="BusUp" /></Link>
        <div className="bzc-erro-topo-fim">
          <BotaoTema />
          <a className="bzc-erro-ajuda" href={`mailto:${EMAIL_VENDAS}`}>{t.help}</a>
          {ESTADO_URL ? <Link className="bzc-btn bzc-btn--navy bzc-btn--sm" to={ESTADO_URL}>{t.statusPage}</Link> : null}
        </div>
      </header>

      <main className="bzc-erro-corpo" id="conteudo">
        <div className="bzc-erro-in">
          <span className="bzc-erro-pilula"><i className="bzc-ponto bzc-pulsa" />{e.pilula}</span>
          <span aria-hidden className="bzc-erro-codigo">{e.codigo}</span>
          <h1 className="bzc-erro-h1">{e.titulo}</h1>
          <p className="bzc-erro-lead">{e.lead}</p>

          <div className="bzc-erro-accoes">
            <Accao className="bzc-btn bzc-btn--azul" para={destino.um}>{e.cta1}</Accao>
            <Accao className="bzc-btn bzc-btn--linha" para={destino.dois}>{e.cta2}</Accao>
          </div>

          <ul className="bzc-erro-pistas">
            {e.pistas.map((h) => (
              <li key={h.k}>
                <b>{h.k}</b>
                <span>{h.v}</span>
              </li>
            ))}
          </ul>

          <span className="bzc-erro-ref">{ref}</span>
        </div>
      </main>

      <footer className="bzc-erro-rodape">
        <span className="bzc-rotulo">{t.poweredBy}</span>
        <LogotipoUpDigital alt="UpDigital, Limitada" altura={24} />
      </footer>
    </div>
  );
}

/** Um destino vazio quer dizer "repetir o que falhou", e isso é um botão e não
 *  uma ligação: não há endereço para onde ir. */
function Accao({ para, className, children }: { para: string; className: string; children: React.ReactNode }) {
  if (!para) {
    return <button className={className} onClick={() => window.location.reload()} type="button">{children}</button>;
  }
  return <Link className={className} to={para}>{children}</Link>;
}

/** O 404 do encaminhador. Existe em separado para a rota `*` ficar legível. */
export function BusUpNaoEncontrado() {
  return <BusUpErroPage chave="404" />;
}

/** Os seis estados num só ecrã, para os rever sem os provocar. Só em dev. */
export function BusUpErrosDemo() {
  const { lang } = useLandingPrefs();
  const chaves = copyErros(lang).erros.map((x) => x.chave);
  const [qual, setQual] = useState<ChaveErro>("404");
  return (
    <>
      <div className="bzc-erro-demo">
        {chaves.map((k) => (
          <button aria-pressed={k === qual} key={k} onClick={() => setQual(k)} type="button">{k}</button>
        ))}
      </div>
      <BusUpErroPage chave={qual} />
    </>
  );
}
