import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, ArrowRight, Search } from "lucide-react";
import StopCombo, { type ComboOpt } from "../booking/StopCombo";
import { CampoData } from "../../ui/CampoData";
import { CampoSelect } from "../../ui/CampoSelect";
import { useTpmCopy } from "./tpm-copy";

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
 *  a pessoa a um ecra vazio. */

const pad = (n: number) => String(n).padStart(2, "0");
const paraIso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export default function HeroBooking() {
  const { t } = useTpmCopy();
  const b = t.heroBusca;
  const navegar = useNavigate();
  const [stops, setStops] = useState<ComboOpt[]>([]);
  const [origem, setOrigem] = useState("");
  const [destino, setDestino] = useState("");
  const [tipo, setTipo] = useState<"ida" | "idaevolta">("ida");
  const [data, setData] = useState("");
  const [volta, setVolta] = useState("");
  const [pax, setPax] = useState("1");
  const [erro, setErro] = useState("");

  const hoje = useMemo(() => paraIso(new Date()), []);

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

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    if (!origem || !destino) { setErro("Indique a origem e o destino."); return; }
    if (origem === destino) { setErro("A origem e o destino não podem ser o mesmo lugar."); return; }
    if (!data) { setErro("Escolha a data de ida."); return; }
    if (tipo === "idaevolta" && !volta) { setErro("Escolha a data de regresso."); return; }
    setErro("");

    const q = new URLSearchParams({ origem, destino, data, pax });
    if (tipo === "idaevolta" && volta) q.set("volta", volta);
    navegar(`/comprar?${q}`);
  };

  const semParagens = stops.length === 0;

  return (
    /* O cartao nao tem titulo visivel. Tinha "Encontre a sua viagem", que
       repetia o <h1> a dois centimetros de distancia e custava os 33px que
       faltavam para a fila de campos caber na dobra. O nome continua a
       existir para quem navega por leitor de ecra, em `aria-label`. */
    <form className="tpm-busca" onSubmit={submeter} aria-label={b.titulo}>
      <div className="tpm-busca-topo">
        <div className="tpm-busca-tipo" role="group" aria-label={b.tipoViagem}>
          {([["ida", b.soIda], ["idaevolta", b.idaVolta]] as const).map(([chave, rotulo]) => (
            <button
              aria-pressed={tipo === chave}
              className={`tpm-busca-tipo-btn${tipo === chave ? " is-on" : ""}`}
              key={chave}
              onClick={() => { setTipo(chave); if (chave === "ida") setVolta(""); }}
              type="button"
            >
              {chave === "ida" ? <ArrowRight aria-hidden size={15} /> : <ArrowLeftRight aria-hidden size={15} />}
              {rotulo}
            </button>
          ))}
        </div>
      </div>

      <div className={`tpm-busca-campos${tipo === "idaevolta" ? " tem-volta" : ""}`}>
        {/* `is-largo`: em telemovel a origem e o destino ocupam a fila toda e
            as datas ficam a par. Marcado por classe, e nao por `nth-child`,
            porque a coluna da volta aparece e desaparece e mudava a contagem. */}
        <div className="tpm-busca-campo is-largo">
          <label htmlFor="busca-origem">{b.origem}</label>
          <StopCombo
            exclude={destino}
            id="busca-origem"
            onChange={setOrigem}
            placeholder={semParagens ? b.semPartidas : b.deOnde}
            stops={stops}
            value={origem}
          />
        </div>

        {/* O botao de inverter vive ENTRE os dois campos, e nao ao lado: e ali
            que a pessoa olha quando percebe que trocou os lugares. */}
        <button
          aria-label={b.trocar}
          className="tpm-busca-inverter"
          onClick={inverter}
          title={b.trocar}
          type="button"
        >
          <ArrowLeftRight aria-hidden size={16} />
        </button>

        <div className="tpm-busca-campo is-largo">
          <label htmlFor="busca-destino">{b.destino}</label>
          <StopCombo
            exclude={origem}
            id="busca-destino"
            onChange={setDestino}
            placeholder={semParagens ? b.semPartidas : b.paraOnde}
            stops={stops}
            value={destino}
          />
        </div>

        <div className="tpm-busca-campo">
          <label htmlFor="busca-data">{b.ida}</label>
          {/* `min={hoje}`: nao se vende bilhete para ontem. */}
          <CampoData id="busca-data" limpavel={false} min={hoje} onChange={setData} value={data} vazio={b.dataVazia} />
        </div>

        {tipo === "idaevolta" && (
          <div className="tpm-busca-campo">
            <label htmlFor="busca-volta">{b.volta}</label>
            {/* O regresso nunca antes da ida. */}
            <CampoData id="busca-volta" limpavel={false} min={data || hoje} onChange={setVolta} value={volta} vazio={b.dataVazia} />
          </div>
        )}

        <CampoSelect
          className="tpm-busca-campo"
          label={b.passageiros}
          onChange={setPax}
          value={pax}
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>{n} {n === 1 ? b.passageiro1 : b.passageiroN}</option>
          ))}
        </CampoSelect>

        {/* O botao voltou para o fim da fila dos campos. Estava numa linha
            propria porque, com a volta ligada, a fila ganhava uma coluna e o
            botao encolhia ate "Procurar" quebrar em duas linhas; a coluna dele
            passou a ter `minmax(190px, auto)` no CSS, que e a largura que o
            rotulo mais o icone precisam, e o problema deixou de existir. A
            linha que ele ocupava custava 76px — era o que faltava para o
            cartao caber na dobra.

            Com ele saiu tambem a fila de atalhos de destino. Era ruido na
            unica superficie da pagina onde se vende: quatro paragens sem
            ordem de importancia (nao ha dados de procura) ao lado dos campos
            onde a pessoa ja estava a escrever o destino. */}
        <button className="tpm-busca-btn" disabled={semParagens} type="submit">
          <Search aria-hidden size={18} /> {b.procurar}
        </button>
      </div>

      {erro ? <p className="tpm-busca-erro" role="alert">{erro}</p> : null}
    </form>
  );
}
