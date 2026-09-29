import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, BedDouble, Info } from "lucide-react";
import CheRevela from "./CheRevela";
import CheetahPagina, { CheetahIntro, useCheetahMeta } from "./CheetahChrome";
import { useCheetahCopy } from "./cheetah-copy";

/* Horários e preços. Os factos — paragens, horas, valores — vêm dos quadros do
 * site oficial. Duas coisas foram corrigidas pelo caminho e estão explicadas em
 * `cheetah-copy.ts`: a grafia "Tofu" passa a Tofo, e os dias de partida seguem
 * os QUADROS oficiais, que contradizem o texto de apresentação do mesmo site.
 *
 * A PÁGINA ESTÁ ORGANIZADA À VOLTA DA VIAGEM, e não do bloco de horário.
 * Antes, o Maputo ↔ Nelspruit tinha quatro quadros — "Parte de Moçambique",
 * "Chega a Nelspruit", "Parte de Nelspruit", "Chega a Moçambique". São duas
 * viagens, não quatro listas, e quem lia tinha de as colar de cabeça para
 * saber que sai às 05:30 e chega às 10:00. Agora cada painel é uma viagem
 * inteira, da primeira paragem à última, com o tempo previsto no topo.
 *
 * O quadro é uma `<table>` a sério e não uma grelha de `<div>`: isto são dados
 * tabulares, e quem usa leitor de ecrã precisa de os poder navegar por linha e
 * coluna. Abaixo de 768px cada linha vira cartão — por CSS, sem mudar o
 * markup, para a semântica não depender da largura do ecrã.
 */

/** A duração de um painel é a diferença entre a primeira e a última hora
 *  publicadas. Vive aqui e não no dicionário PORQUE É DERIVADA: escrita à mão,
 *  divergia dos dados no dia em que uma hora mudasse, e ninguém daria por ela.
 *
 *  O `+ 24h` cobre a travessia da meia-noite. Nenhum percurso actual a faz,
 *  mas a conta não custa nada e um valor negativo seria um disparate visível. */
function duracao(inicio: string, fim: string) {
  const min = (h: string) => Number(h.slice(0, 2)) * 60 + Number(h.slice(3, 5));
  let d = min(fim) - min(inicio);
  if (d < 0) d += 24 * 60;
  const horas = Math.floor(d / 60);
  const resto = d % 60;
  return resto ? `${horas}h${String(resto).padStart(2, "0")}` : `${horas}h`;
}

/** A cor e a seta de cada distintivo. Vivem aqui e não no dicionário porque
 *  são estrutura: traduzir "che-sent--ida" não faria sentido. O que muda com a
 *  língua é só a palavra, e essa vem de `sentidos`. */
const SENTIDO_SETA = { ida: ArrowRight, volta: ArrowLeft, unico: ArrowRight } as const;

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

          {/* O RESUMO ANTES DO DETALHE. Cinco cartões parecidos obrigavam a
              ler os cinco para saber em que dias se vai de Maputo ao Tofo.
              Aqui responde-se numa vista, e o nome leva ao cartão. */}
          <CheRevela>
            <div className="che-resumo">
              <h2>{h.resumo.h2}</h2>
              <table className="che-quadro che-quadro--resumo">
                <caption className="sr-only">{h.resumo.legenda}</caption>
                <thead>
                  <tr>
                    <th scope="col">{h.resumo.percurso}</th>
                    <th scope="col">{h.resumo.dias}</th>
                    <th scope="col">{h.resumo.duracao}</th>
                    <th scope="col">{h.resumo.preco}</th>
                  </tr>
                </thead>
                <tbody>
                  {h.percursos.map((p) => (
                    <tr key={p.id}>
                      <td><a href={`#${p.id}`}>{p.nome}</a></td>
                      {/* `data-rot` da o rotulo de volta em ecra estreito, onde
                          o cabecalho da tabela desaparece. Escrito aqui e nao
                          repetido no markup visivel: a tabela continua a ser
                          uma tabela para quem a navega por linha e coluna. */}
                      <td data-rot={h.resumo.dias}>{p.dias}</td>
                      <td data-rot={h.resumo.duracao}>{p.duracao}</td>
                      <td data-rot={h.resumo.preco}>{p.desde ? `${h.desde} ${p.preco}` : p.preco}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CheRevela>

          <div className="che-percursos">
            {h.percursos.map((p) => (
              <CheRevela key={p.id}>
                <article className="che-percurso" id={p.id}>
                  <header className="che-percurso-head">
                    <div>
                      <h2>{p.nome}</h2>
                      <p className="che-percurso-dias">{p.diasLongo} · {p.duracao}</p>
                      {p.nota ? <p className="che-percurso-nota">{p.nota}</p> : null}
                    </div>
                    {/* O PREÇO SUBIU PARA O CABEÇALHO. Estava no fim do cartão,
                        depois de todos os quadros, quando é das primeiras
                        coisas que se decide. */}
                    <p className="che-percurso-preco">
                      <span>{p.desde ? h.precoDesdeRotulo : h.precoRotulo}</span>
                      <strong>{p.preco}</strong>
                    </p>
                  </header>

                  <div className={`che-percurso-corpo${p.paineis.length > 1 ? " tem-dois" : ""}`}>
                    {p.paineis.map((painel) => {
                      const ini = painel.linhas[0][2];
                      const fim = painel.linhas[painel.linhas.length - 1][2];
                      const Seta = SENTIDO_SETA[painel.tipo as keyof typeof SENTIDO_SETA];
                      return (
                        <div className={`che-painel che-sent--${painel.tipo}`} key={painel.t}>
                          <div className="che-painel-head">
                            <span className="che-painel-sent">
                              {Seta ? <Seta size={13} aria-hidden /> : null}
                              {h.sentidos[painel.tipo]}
                            </span>
                            <h3>{painel.t}</h3>
                          </div>
                          <p className="che-painel-meta">
                            {h.parte} {ini} · {h.chega} {fim} · {h.cerca} {duracao(ini, fim)}
                          </p>

                          <table className="che-quadro">
                            {/* A legenda diz de que quadro se trata a quem o
                                encontra fora de contexto — num leitor de ecrã,
                                numa lista de tabelas da página. */}
                            <caption className="sr-only">{painel.t} — {h.legendaQuadro}</caption>
                            <thead>
                              <tr>
                                <th scope="col">{h.colunas.paragem}</th>
                                <th scope="col">{h.colunas.hora}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {painel.linhas.map((linha, n) => {
                                /* PARTE e CHEGA são PALAVRAS e não cores: quem
                                   não distinga tons continua a saber qual é a
                                   primeira paragem e qual é a última. */
                                const extremo =
                                  n === 0 ? h.parte
                                  : n === painel.linhas.length - 1 ? h.chega
                                  : "";
                                return (
                                  <tr key={`${linha[0]}-${linha[1]}-${linha[2]}`}>
                                    <td>
                                      {extremo ? <span className="che-extremo">{extremo}</span> : null}
                                      <span className="che-paragem-nome">{linha[0]}</span>
                                      <span className="che-paragem-local">{linha[1]}</span>
                                    </td>
                                    <td>{linha[2]}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      );
                    })}
                  </div>

                  {(p.dormida || p.precos.length > 0) && (
                    <div className="che-percurso-pe">
                      {p.dormida ? (
                        <p className="che-dormida">
                          <BedDouble size={16} aria-hidden /> {p.dormida}
                        </p>
                      ) : null}
                      {p.precos.length > 0 ? (
                        <div className="che-precos">
                          <p className="che-precos-rot">{h.precoDetalhe}</p>
                          <ul>
                            {p.precos.map((preco) => <li key={preco}>{preco}</li>)}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  )}
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
