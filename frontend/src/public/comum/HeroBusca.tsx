import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, ArrowRight, Search } from "lucide-react";
import StopCombo, { type ComboOpt } from "../booking/StopCombo";
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
};

const pad = (n: number) => String(n).padStart(2, "0");
const paraIso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export default function HeroBusca({ textos: b }: { textos: TextosBusca }) {
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

  const submeter = (e: FormEvent) => {
    e.preventDefault();
    if (!origem || !destino) { setErro(b.erroPercurso); return; }
    if (origem === destino) { setErro(b.erroMesmoLugar); return; }
    if (!data) { setErro(b.erroData); return; }
    if (tipo === "idaevolta" && !volta) { setErro(b.erroVolta); return; }
    setErro("");

    const q = new URLSearchParams({ origem, destino, data, pax });
    if (tipo === "idaevolta" && volta) q.set("volta", volta);
    navegar(`/comprar?${q}`);
  };

  const semParagens = stops.length === 0;

  return (
    <form className="bz-busca" onSubmit={submeter}>
      <div className="bz-busca-topo">
        <h2 className="bz-busca-titulo">{b.titulo}</h2>
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
      </div>

      <div className={`bz-busca-campos${tipo === "idaevolta" ? " tem-volta" : ""}`}>
        <div className="bz-busca-campo">
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
          className="bz-busca-inverter"
          onClick={inverter}
          title={b.trocar}
          type="button"
        >
          <ArrowLeftRight aria-hidden size={16} />
        </button>

        <div className="bz-busca-campo">
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

        <div className="bz-busca-campo">
          <label htmlFor="busca-data">{b.ida}</label>
          {/* `min={hoje}`: nao se vende bilhete para ontem. */}
          <CampoData id="busca-data" limpavel={false} min={hoje} onChange={setData} value={data} vazio={b.dataVazia} />
        </div>

        {tipo === "idaevolta" && (
          <div className="bz-busca-campo">
            <label htmlFor="busca-volta">{b.volta}</label>
            {/* O regresso nunca antes da ida. */}
            <CampoData id="busca-volta" limpavel={false} min={data || hoje} onChange={setVolta} value={volta} vazio={b.dataVazia} />
          </div>
        )}

        <CampoSelect
          className="bz-busca-campo"
          label={b.passageiros}
          onChange={setPax}
          value={pax}
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>{n} {n === 1 ? b.passageiro1 : b.passageiroN}</option>
          ))}
        </CampoSelect>
      </div>

      {/* O botao vive numa linha propria, e nao no fim da fila dos campos:
          com a volta ligada a fila ganha uma coluna e o botao encolhia ate
          "Procurar" quebrar em duas linhas. */}
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
        <button className="bz-busca-btn" disabled={semParagens} type="submit">
          <Search aria-hidden size={18} /> {b.procurar}
        </button>
      </div>

      {erro ? <p className="bz-busca-erro" role="alert">{erro}</p> : null}
    </form>
  );
}
