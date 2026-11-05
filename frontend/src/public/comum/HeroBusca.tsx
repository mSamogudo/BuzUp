import { useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, ArrowRight, Search } from "lucide-react";
import StopCombo, { type ComboOpt, type StopComboControlo } from "../booking/StopCombo";
import { CampoData } from "../../ui/CampoData";
import { CampoSelect } from "../../ui/CampoSelect";

/** A compra comeca no hero, e nao a um clique de distancia.
 *
 *  Nao duplica o fluxo: monta o link que o `/comprar` ja sabe ler
 *  (`origem`, `destino`, `data`, `volta`, `pax`) e entrega-lhe o trabalho.
 *  Com percurso e data completos, essa pagina pesquisa sozinha e abre
 *  directamente na lista de partidas — quem preenche aqui nao repete nada
 *  do outro lado.
 *
 *  As paragens vem de `sellable=1`, que so devolve origens e destinos com
 *  partidas futuras a venda. Oferecer um percurso sem partidas seria mandar
 *  a pessoa a um ecra vazio.
 *
 *  VIVE AQUI, e nao na pasta de um operador, porque nada nele e de marca:
 *  as cores saem de variaveis que a caixa do site define (`--busca-*`, ver
 *  `busca.css`) e o texto entra por `textos`. Nasceu dentro da TPM-TUR e
 *  saiu de la quando a Cheetah Express passou a precisar do mesmo cartao —
 *  duplica-lo seria criar um segundo sitio onde os mesmos erros voltam.
 */

/** O que o cartao precisa de saber dizer. Cada operador traz o seu dicionario;
 *  a forma e esta e e verificada pelo compilador nos dois lados. */
export type TextosBusca = {
  titulo: string;
  tipoViagem: string;
  soIda: string;
  idaVolta: string;
  origem: string;
  destino: string;
  ida: string;
  volta: string;
  trocar: string;
  procurar: string;
  destinosAVenda: string;
  semPartidas: string;
  /** Enquanto a lista de paragens ainda nao chegou. */
  aCarregar: string;
  deOnde: string;
  paraOnde: string;
  passageiros: string;
  passageiro1: string;
  passageiroN: string;
  dataVazia: string;
  /* Os erros estavam em portugues fixo dentro do componente: quem punha o site
     em ingles continuava a receber "Indique a origem e o destino.". Passaram
     para aqui quando o cartao saiu da TPM-TUR. */
  erroPercurso: string;
  erroMesmoLugar: string;
  erroData: string;
  erroVolta: string;
  /* Lista de paragens sem resultado. Tambem estava fixa em portugues, dentro
     do StopCombo. */
  semParagem: string;
  /* A data escolhida mostra-se por extenso ("Hoje, qui 5 nov") em vez de
     dd/mm/aaaa: le-se sem contar dias. A lingua do Intl vem daqui e nao do
     browser, pela mesma razao que o CampoData existe. */
  locale: string;
  hoje: string;
  amanha: string;
  /** Texto do campo da volta ainda vazio. */
  voltaVazia: string;
  /** Botao que fecha a lista de paragens em ecra inteiro, no telemovel. */
  fechar: string;
};

type Campo = "origem" | "destino" | "data" | "volta";

const pad = (n: number) => String(n).padStart(2, "0");
const paraIso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** "qui 5 nov" / "Thu 5 Nov", com "Hoje," ou "Amanha," a frente quando cabe.
 *  Monta-se pelas partes do Intl porque o formato inteiro em pt traz pontos
 *  e "de" ("qui., 5 de nov."), que num campo de 24px so fazem ruido. */
function dataAmiga(d: Date, b: TextosBusca) {
  const partes = new Intl.DateTimeFormat(b.locale, { weekday: "short", day: "numeric", month: "short" }).formatToParts(d);
  const p = (t: string) => (partes.find((x) => x.type === t)?.value ?? "").replace(/\./g, "");
  const zero = new Date(); zero.setHours(0, 0, 0, 0);
  const dia = new Date(d); dia.setHours(0, 0, 0, 0);
  const dif = Math.round((dia.getTime() - zero.getTime()) / 86400000);
  /* "Hoje" e "Amanha" tomam o lugar do dia da semana em vez de se juntarem
     a ele: "Amanha, sex 6 nov" nao cabia no segmento a 1440px. */
  const dm = `${p("day")} ${p("month")}`;
  if (dif === 0) return `${b.hoje}, ${dm}`;
  if (dif === 1) return `${b.amanha}, ${dm}`;
  return `${p("weekday")} ${dm}`;
}

/** Como o cartao se apresenta.
 *
 *  `padrao` e o que sempre foi, e e o que a Cheetah Express usa.
 *
 *  `tpm` e o desenho aprovado na tela da TPM-TUR: sem titulo visivel, sem a
 *  fila de atalhos de destino, e com o botao de procurar dentro da fila dos
 *  campos em vez de numa linha propria. Nao e so gosto — a linha propria
 *  custava 76px, e eram esses 76px que faziam o cartao cair fora do primeiro
 *  ecra. A variante existe para que essa mudanca nao chegue a Cheetah, que
 *  partilha este componente e onde ninguem a pediu.
 *
 *  `barra` e o desenho aprovado na tela da Cheetah Express, e vai um passo
 *  alem da `tpm`: o alternador de tipo de viagem desce para DENTRO da fila
 *  dos campos, como primeiro deles, e a fila de cima desaparece por
 *  completo. O cartao passa de 234px a ~112, e foram esses 122px que a
 *  imagem da chapa ganhou para duplicar de tamanho. */
type Variante = "padrao" | "tpm" | "barra";

export default function HeroBusca({ textos: b, variante = "padrao" }: { textos: TextosBusca; variante?: Variante }) {
  /* As duas variantes nao-padrao partilham tres decisoes: o titulo sai do
     ecra, o botao entra na fila dos campos, e a fila de atalhos desaparece.
     Separa-las e o que difere — onde vive o alternador. */
  const compacto = variante !== "padrao";
  const barra = variante === "barra";
  const navegar = useNavigate();
  /* `null` enquanto a lista nao chega. Sem esta distincao, os primeiros
     segundos (ou todos, numa ligacao lenta) diziam "Sem partidas a venda"
     e "Nenhuma paragem com esse nome", e as duas coisas eram falsas. */
  const [carregadas, setStops] = useState<ComboOpt[] | null>(null);
  const stops = useMemo(() => carregadas ?? [], [carregadas]);
  const aCarregar = carregadas === null;
  const [origem, setOrigem] = useState("");
  const [destino, setDestino] = useState("");
  const [tipo, setTipo] = useState<"ida" | "idaevolta">("ida");
  const [data, setData] = useState("");
  const [volta, setVolta] = useState("");
  const [pax, setPax] = useState("1");
  const [erro, setErro] = useState("");
  /* Qual campo esta em falta. A mensagem continua por baixo (role=alert),
     mas o campo tambem fica marcado e recebe o foco: antes a pessoa lia
     "Indique a origem e o destino" e tinha de descobrir sozinha qual. */
  const [campoErro, setCampoErro] = useState<Campo | null>(null);
  const [dataAberta, setDataAberta] = useState(false);
  const [voltaAberta, setVoltaAberta] = useState(false);
  const origemRef = useRef<StopComboControlo>(null);
  const destinoRef = useRef<StopComboControlo>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);

  const hoje = useMemo(() => paraIso(new Date()), []);

  /** Atalhos de destino. Nao sao "populares" — nao ha dados de procura — sao
   *  simplesmente paragens que o `sellable=1` devolveu, ou seja, que tem
   *  partidas futuras a venda. Chamar-lhes outra coisa seria inventar. */
  const atalhos = useMemo(
    () => stops.filter((s) => String(s.id) !== origem && String(s.id) !== destino).slice(0, 4),
    [stops, origem, destino],
  );

  useEffect(() => {
    let vivo = true;
    fetch("/api/public/trips/?sellable=1", { headers: { "Content-Type": "application/json" } })
      .then((r) => r.json())
      .then((d) => { if (vivo) setStops(d.stops || []); })
      .catch(() => { if (vivo) setStops([]); });
    return () => { vivo = false; };
  }, []);

  /** Trocar origem por destino. Quem se engana a escrever nao tem de apagar
   *  os dois campos e recomecar. */
  const inverter = () => {
    setOrigem(destino);
    setDestino(origem);
  };

  // Quem corrige o campo nao precisa de continuar a ler o erro.
  useEffect(() => { setErro(""); setCampoErro(null); }, [origem, destino, data, volta, tipo]);

  /* Cada escolha leva ao passo seguinte que ainda falta: origem -> destino
     -> calendario -> (volta) -> botao. Sao dois cliques a menos numa
     pesquisa completa, e ninguem fica a pensar "e agora?". Nunca submete
     sozinho: o ultimo passo e sempre da pessoa. */
  const seguinte = (feito: Campo) => {
    const falta = (c: Campo) => (c === "origem" ? !origem && feito !== "origem"
      : c === "destino" ? !destino && feito !== "destino"
      : c === "data" ? !data && feito !== "data"
      : tipo === "idaevolta" && !volta && feito !== "volta");
    if (falta("destino")) destinoRef.current?.abrir();
    else if (falta("origem")) origemRef.current?.abrir();
    else if (falta("data")) setDataAberta(true);
    else if (falta("volta")) setVoltaAberta(true);
    else botaoRef.current?.focus();
  };

  const assinalar = (c: Campo, msg: string) => {
    setErro(msg);
    setCampoErro(c);
    if (c === "origem") origemRef.current?.focar();
    else if (c === "destino") destinoRef.current?.focar();
    else if (c === "data") setDataAberta(true);
    else setVoltaAberta(true);
  };

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    if (!origem) { assinalar("origem", b.erroPercurso); return; }
    if (!destino) { assinalar("destino", b.erroPercurso); return; }
    if (origem === destino) { assinalar("destino", b.erroMesmoLugar); return; }
    if (!data) { assinalar("data", b.erroData); return; }
    if (tipo === "idaevolta" && !volta) { assinalar("volta", b.erroVolta); return; }
    setErro("");

    const q = new URLSearchParams({ origem, destino, data, pax });
    if (tipo === "idaevolta" && volta) q.set("volta", volta);
    navegar(`/comprar?${q}`);
  };

  const semParagens = !aCarregar && stops.length === 0;
  const formatar = (d: Date) => dataAmiga(d, b);
  const idiomaCalendario = b.locale.startsWith("pt") ? "pt" : "en";

  /** Um clique em qualquer parte do segmento, e nao so no texto, abre o
   *  controlo. Na barra da TPM o segmento tem 64px de altura e o controlo 24:
   *  o resto era area morta que parecia clicavel. */
  const focarSegmento = (e: MouseEvent<HTMLDivElement>) => {
    const alvo = e.target as HTMLElement;
    if (!alvo.classList.contains("bz-busca-campo")) return;
    const controlo = alvo.querySelector<HTMLElement>("input, button");
    controlo?.focus();
    controlo?.click();
  };

  /* O alternador de tipo de viagem. Vive na fila de cima nas variantes
     `padrao` e `tpm`, e dentro da fila dos campos na `barra` — por isso e uma
     variavel e nao markup repetido nos dois sitios. */
  const alternador = (
    <div className="bz-busca-tipo" role="group" aria-label={b.tipoViagem}>
      {([["ida", b.soIda], ["idaevolta", b.idaVolta]] as const).map(([chave, rotulo]) => (
        <button
          aria-pressed={tipo === chave}
          className={`bz-busca-tipo-btn${tipo === chave ? " is-on" : ""}`}
          key={chave}
          onClick={() => { setTipo(chave); if (chave === "ida") setVolta(""); }}
          type="button"
        >
          {chave === "ida" ? <ArrowRight aria-hidden size={15} /> : <ArrowLeftRight aria-hidden size={15} />}
          {rotulo}
        </button>
      ))}
    </div>
  );

  return (
    <form
      aria-label={compacto ? b.titulo : undefined}
      className={`bz-busca${compacto ? ` bz-busca--${variante}` : ""}`}
      onSubmit={submeter}
    >
      {/* Nas variantes compactas o titulo sai do ecra mas nao do documento:
          vive no `aria-label` do formulario, para quem navega por leitor de
          ecra continuar a saber o que este bloco e. Na `barra` a fila de cima
          desaparece de todo — nao sobra nada para ela. */}
      {barra ? null : (
        <div className="bz-busca-topo">
          {compacto ? null : <h2 className="bz-busca-titulo">{b.titulo}</h2>}
          {alternador}
        </div>
      )}

      <div className={`bz-busca-campos${tipo === "idaevolta" ? " tem-volta" : ""}`}>
        {/* Os campos, sem o botao. Na `tpm` e esta caixa que desenha a barra
            unica com divisorias; nas outras variantes e `display: contents` e
            nao existe para o layout. */}
        <div className="bz-busca-segmentos" onClick={focarSegmento}>
        {barra ? (
          /* Um campo como os outros: rotulo por cima, controlo por baixo. E um
             `<span>` e nao um `<label>` porque o que ele nomeia sao dois
             botoes e nao um controlo — quem os agrupa e o `role="group"` com
             o seu proprio `aria-label`, e um `for` aqui nao teria alvo. */
          <div className="bz-busca-campo">
            <span aria-hidden>{b.tipoViagem}</span>
            {alternador}
          </div>
        ) : null}

        <div className={`bz-busca-campo is-largo is-origem${campoErro === "origem" ? " is-erro" : ""}`}>
          <label htmlFor="busca-origem">{b.origem}</label>
          <StopCombo
            emptyText={aCarregar ? b.aCarregar : b.semParagem}
            exclude={destino}
            fechar={b.fechar}
            folha
            id="busca-origem"
            invalido={campoErro === "origem"}
            onChange={setOrigem}
            onEscolha={() => seguinte("origem")}
            placeholder={semParagens ? b.semPartidas : b.deOnde}
            ref={origemRef}
            rotulo={b.origem}
            stops={stops}
            value={origem}
          />
        </div>

        {/* O botao de inverter vive ENTRE os dois campos, e nao ao lado: e ali
            que a pessoa olha quando percebe que trocou os lugares. */}
        <button
          aria-label={b.trocar}
          className="bz-busca-inverter"
          onClick={inverter}
          title={b.trocar}
          type="button"
        >
          <ArrowLeftRight aria-hidden size={16} />
        </button>

        <div className={`bz-busca-campo is-largo is-destino${campoErro === "destino" ? " is-erro" : ""}`}>
          <label htmlFor="busca-destino">{b.destino}</label>
          <StopCombo
            emptyText={aCarregar ? b.aCarregar : b.semParagem}
            exclude={origem}
            fechar={b.fechar}
            folha
            id="busca-destino"
            invalido={campoErro === "destino"}
            onChange={setDestino}
            onEscolha={() => seguinte("destino")}
            placeholder={semParagens ? b.semPartidas : b.paraOnde}
            ref={destinoRef}
            rotulo={b.destino}
            stops={stops}
            value={destino}
          />
        </div>

        <div className={`bz-busca-campo is-data${campoErro === "data" ? " is-erro" : ""}`}>
          <label htmlFor="busca-data">{b.ida}</label>
          {/* `min={hoje}`: nao se vende bilhete para ontem. */}
          <CampoData
            aberto={dataAberta}
            depoisDeEscolher={() => seguinte("data")}
            formatar={formatar}
            id="busca-data"
            idioma={idiomaCalendario}
            invalido={campoErro === "data"}
            limpavel={false}
            min={hoje}
            onAbertoChange={setDataAberta}
            onChange={(v) => { setData(v); if (volta && v > volta) setVolta(""); }}
            value={data}
            vazio={b.dataVazia}
          />
        </div>

        {tipo === "idaevolta" && (
          <div className={`bz-busca-campo is-data is-volta${campoErro === "volta" ? " is-erro" : ""}`}>
            <label htmlFor="busca-volta">{b.volta}</label>
            {/* O regresso nunca antes da ida. */}
            <CampoData
              aberto={voltaAberta}
              depoisDeEscolher={() => seguinte("volta")}
              formatar={formatar}
              id="busca-volta"
              idioma={idiomaCalendario}
              invalido={campoErro === "volta"}
              limpavel={false}
              min={data || hoje}
              onAbertoChange={setVoltaAberta}
              onChange={setVolta}
              value={volta}
              vazio={b.voltaVazia}
            />
          </div>
        )}

        <CampoSelect
          className="bz-busca-campo is-pax"
          label={b.passageiros}
          onChange={setPax}
          value={pax}
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>{n} {n === 1 ? b.passageiro1 : b.passageiroN}</option>
          ))}
        </CampoSelect>
        </div>

        {compacto ? (
          <button className="bz-busca-btn" disabled={semParagens} ref={botaoRef} type="submit">
            <Search aria-hidden size={18} /> {b.procurar}
          </button>
        ) : null}
      </div>

      {/* Na variante `padrao` o botao vive numa linha propria porque, com a
          volta ligada, a fila ganha uma coluna e o botao encolhia ate
          "Procurar" quebrar em duas linhas. Na `tpm` o botao esta dentro da
          fila e a coluna dele leva uma largura minima no CSS, que resolve o
          mesmo problema sem gastar uma linha inteira. */}
      {compacto ? null : (
        <div className="bz-busca-baixo">
          {atalhos.length > 0 && !destino ? (
            <div className="bz-busca-atalhos">
              <span className="bz-busca-atalhos-rotulo">{b.destinosAVenda}</span>
              {atalhos.map((s) => (
                <button className="bz-busca-atalho" key={s.id} onClick={() => setDestino(String(s.id))} type="button">
                  {s.name}
                </button>
              ))}
            </div>
          ) : <span />}
          <button className="bz-busca-btn" disabled={semParagens} ref={botaoRef} type="submit">
            <Search aria-hidden size={18} /> {b.procurar}
          </button>
        </div>
      )}

      {erro ? <p className="bz-busca-erro" role="alert">{erro}</p> : null}
    </form>
  );
}
