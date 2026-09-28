import CheRevela from "./CheRevela";
import { FileWarning } from "lucide-react";
import CheetahPagina, { CheetahIntro, EMAIL_RESERVAS, useCheetahMeta } from "./CheetahChrome";
import { useCheetahCopy } from "./cheetah-copy";

/* Condições de transporte.
 *
 * ESTE TEXTO NÃO VEM DO SITE OFICIAL, e é deliberado. A página "Terms and
 * Conditions" de cheetah-express.com são os termos de SERVIÇO SaaS do
 * drivenot.com — o fornecedor de reservas que o BusUp vem substituir. Nomeiam
 * esse fornecedor como prestador, dão-lhe exclusividade de sistema de reservas
 * em Moçambique e remetem para tribunais sul-africanos. Reproduzi-los aqui
 * seria publicar, em nome da Cheetah, o contrato do fornecedor que ela está a
 * deixar.
 *
 * O que está escrito são condições de TRANSPORTE, derivadas da operação real —
 * embarque, bagagem, travessia de fronteira, alterações. Está marcado como
 * provisório no topo da página e continua a precisar do aval da Cheetah
 * Express antes de valer como documento.
 */

/** Converte `{email}` numa ligação. As condições referem o endereço de
 *  reservas no último ponto; escrevê-lo no dicionário como texto solto dava
 *  um email que não se podia clicar. */
function comEmail(texto: string) {
  return texto.split(/(\{email\})/).map((parte, i) =>
    parte === "{email}"
      ? <a key={i} href={`mailto:${EMAIL_RESERVAS}`}>{EMAIL_RESERVAS}</a>
      : <span key={i}>{parte}</span>,
  );
}

const id = (n: number) => `condicao-${n + 1}`;

export default function TermosPage() {
  const { t } = useCheetahCopy();
  const c = t.termos;

  useCheetahMeta(c.meta.titulo, c.meta.descricao);

  return (
    <CheetahPagina activa="/cheetah-express/termos">
      <CheetahIntro migalha={c.migalha} titulo={c.titulo} descricao={c.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          {/* O aviso de que o texto é provisório fica no TOPO e não no rodapé:
              quem o lê tem de o saber antes de o ler, não depois. */}
          <p className="che-rascunho">
            <FileWarning size={19} aria-hidden />
            <span>{c.porAprovar}</span>
          </p>

          <div className="che-termos">
            {/* Um índice, e não uma parede de texto: são dez secções e quem
                chega aqui vem quase sempre atrás de uma. */}
            <nav className="che-termos-indice" aria-label={c.titulo}>
              <h2>{c.migalha}</h2>
              <ol>
                {c.seccoes.map((s, n) => (
                  <li key={s.h}><a href={`#${id(n)}`}>{s.h}</a></li>
                ))}
              </ol>
            </nav>

            <div className="che-termos-corpo">
              {c.seccoes.map((s, n) => (
                <CheRevela key={s.h}>
                  <article className="che-termo" id={id(n)}>
                    <h2>{s.h}</h2>
                    {s.p.map((paragrafo) => (
                      <p key={paragrafo}>{comEmail(paragrafo)}</p>
                    ))}
                  </article>
                </CheRevela>
              ))}
            </div>
          </div>
        </div>
      </section>
    </CheetahPagina>
  );
}
