import { Link } from "react-router-dom";
import { ArrowRight, BedDouble, Info } from "lucide-react";
import CheRevela from "./CheRevela";
import CheetahPagina, { CheetahIntro, useCheetahMeta } from "./CheetahChrome";
import { useCheetahCopy } from "./cheetah-copy";

/* Horários e preços. Os factos — paragens, horas, valores — vêm dos quadros do
 * site oficial. Duas coisas foram corrigidas pelo caminho e estão explicadas em
 * `cheetah-copy.ts`: a grafia "Tofu" passa a Tofo, e os dias de partida seguem
 * os QUADROS oficiais, que contradizem o texto de apresentação do mesmo site.
 *
 * O quadro é uma `<table>` a sério e não uma grelha de `<div>`: isto são dados
 * tabulares, e quem usa leitor de ecrã precisa de os poder navegar por linha e
 * coluna. Abaixo de 768px cada linha vira cartão — por CSS, sem mudar o
 * markup, para a semântica não depender da largura do ecrã.
 */

export default function HorariosPage() {
  const { t } = useCheetahCopy();
  const h = t.horarios;

  useCheetahMeta(h.meta.titulo, h.meta.descricao);

  return (
    <CheetahPagina activa="/cheetah-express/horarios">
      <CheetahIntro migalha={h.migalha} titulo={h.titulo} descricao={h.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          {/* O aviso da fronteira vem ANTES dos quadros: é a informação que
              faz a diferença entre apanhar e perder uma ligação do outro lado,
              e depois das tabelas ninguém o lia. */}
          <p className="che-aviso">
            <Info size={19} aria-hidden />
            <span>{h.aviso}</span>
          </p>

          <div className="che-percursos">
            {h.percursos.map((p, n) => (
              <CheRevela key={p.id}>
                <article className="che-percurso" id={p.id}>
                  <header className="che-percurso-head">
                    <h2>{p.nome}</h2>
                    <span className="che-percurso-dias">{p.dias}</span>
                  </header>

                  <div className="che-percurso-corpo">
                    {p.blocos.map((bloco) => (
                      <div className="che-bloco" key={bloco.t}>
                        <h3>{bloco.t}</h3>
                        <table className="che-quadro">
                          {/* A legenda diz de que quadro se trata a quem o
                              encontra fora de contexto — num leitor de ecrã,
                              numa lista de tabelas da página. */}
                          <caption className="sr-only">{p.nome} — {bloco.t}</caption>
                          <thead>
                            <tr>
                              <th scope="col">{h.colunas.paragem}</th>
                              <th scope="col">{h.colunas.local}</th>
                              <th scope="col">{h.colunas.hora}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bloco.linhas.map((linha) => (
                              <tr key={`${linha[0]}-${linha[1]}-${linha[2]}`}>
                                <td>{linha[0]}</td>
                                <td>{linha[1]}</td>
                                <td>{linha[2]}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ))}

                    <div className="che-precos">
                      <span className="che-precos-rot">{h.preco}</span>
                      {p.precos.map((preco) => (
                        <span className="che-preco" key={preco}>{preco}</span>
                      ))}
                      <span className="che-preco-nota">{h.soIda}</span>
                      {"dormida" in p && p.dormida && (
                        <span className="che-dormida">
                          <BedDouble size={15} aria-hidden /> {h.incluiDormida}
                        </span>
                      )}
                    </div>
                  </div>
                </article>
              </CheRevela>
            ))}
          </div>
        </div>
      </section>

      <section className="che-cta">
        <div className="bzlp-wrap che-cta-in">
          <div>
            <h2>{h.cta.h2}</h2>
            <p>{h.cta.p}</p>
          </div>
          <div className="che-cta-btns">
            <Link to="/comprar" className="bzlp-btn gold">
              {t.comum.comprarBilhete} <ArrowRight size={17} aria-hidden />
            </Link>
            <Link to="/cheetah-express/contactos" className="bzlp-btn outline">
              {t.comum.falarConnosco}
            </Link>
          </div>
        </div>
      </section>
    </CheetahPagina>
  );
}
