import { useRef, useState } from "react";
import { CalendarDays, X } from "lucide-react";
import { pt, enGB } from "date-fns/locale";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useUi } from "./UiPreferences";

/** Campo de data que mostra sempre `dd/mm/aaaa`.
 *
 *  O `<input type="date">` nativo mostra a data na locale do BROWSER, nao na
 *  da aplicacao. Um telemovel configurado em ingles — coisa comum em
 *  Mocambique — mostrava `mm/dd/aaaa` a quem espera o contrario, e nos
 *  filtros do dashboard isso trocava o intervalo sem ninguem reparar.
 *
 *  O valor que entra e sai continua a ser `AAAA-MM-DD`, para nao mexer em
 *  nada do lado da API. */

const pad = (n: number) => String(n).padStart(2, "0");

/** AAAA-MM-DD a partir do dia civil escolhido.
 *  Nao se usa `toISOString()`: essa converte para UTC e, ao fim da tarde em
 *  Maputo (UTC+2), devolve o dia anterior. */
function paraIso(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function deIso(s: string | undefined): Date | undefined {
  if (!s) return undefined;
  const [a, m, d] = s.split("-").map(Number);
  if (!a || !m || !d) return undefined;
  const data = new Date(a, m - 1, d);
  return Number.isNaN(data.getTime()) ? undefined : data;
}

function paraEcra(d: Date) {
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}

export function CampoData({
  value,
  onChange,
  min,
  max,
  id,
  disabled = false,
  limpavel = true,
  /* O formato mostrado quando ainda nao ha data. O portal segue a sua propria
   * preferencia de idioma (`useUi`), mas as paginas publicas seguem outra — a
   * do selector da landing — e por isso quem chama pode passar o seu. */
  vazio = "dd/mm/aaaa",
  formatar,
  aberto: abertoFora,
  onAbertoChange,
  invalido = false,
  depoisDeEscolher,
  idioma,
}: {
  value: string;
  onChange: (iso: string) => void;
  min?: string;
  max?: string;
  id?: string;
  disabled?: boolean;
  limpavel?: boolean;
  vazio?: string;
  /** Como mostrar a data escolhida. Por omissao `dd/mm/aaaa`; o cartao de
   *  pesquisa das landings passa "Hoje, qui 5 nov", que se le sem contar. */
  formatar?: (d: Date) => string;
  /** Abertura controlada por fora, opcional. O cartao de pesquisa abre o
   *  calendario sozinho depois de escolhido o destino. */
  aberto?: boolean;
  onAbertoChange?: (aberto: boolean) => void;
  invalido?: boolean;
  /** Para onde vai o foco depois de escolhido um dia. Sem isto o Radix
   *  devolve-o ao botao da data, e quem usa o teclado tinha de saltar
   *  sozinho para o passo seguinte. */
  depoisDeEscolher?: () => void;
  /** Idioma do calendario. As landings passam o do seu selector; sem isto o
   *  calendario seguia a preferencia do portal e saia em portugues na pagina
   *  inglesa ("novembro", "seg ter qua"). */
  idioma?: "pt" | "en";
}) {
  const { locale: localeUi } = useUi();
  const locale = idioma ?? localeUi;
  const [abertoProprio, setAbertoProprio] = useState(false);
  const aberto = abertoFora ?? abertoProprio;
  const setAberto = (v: boolean) => { setAbertoProprio(v); onAbertoChange?.(v); };
  const escolheu = useRef(false);
  const caixaRef = useRef<HTMLDivElement>(null);
  const escolhida = deIso(value);
  const minimo = deIso(min);
  const maximo = deIso(max);

  // Uma lista de restricoes, e nao um objecto com campos opcionais: o tipo
  // Matcher exige Date, nao Date | undefined.
  const desactivados: ({ before: Date } | { after: Date })[] = [];
  if (minimo) desactivados.push({ before: minimo });
  if (maximo) desactivados.push({ after: maximo });

  return (
    <Popover onOpenChange={setAberto} open={aberto}>
      <div className="campo-data" ref={caixaRef}>
        <PopoverTrigger aria-invalid={invalido || undefined} className="campo-data-botao" disabled={disabled} id={id} type="button">
          <CalendarDays aria-hidden size={16} />
          {escolhida ? (formatar ?? paraEcra)(escolhida) : <span className="campo-data-vazio">{vazio}</span>}
        </PopoverTrigger>
        {limpavel && value && !disabled ? (
          <button
            aria-label={locale === "pt" ? "Limpar data" : "Clear date"}
            className="campo-data-limpar"
            onClick={() => onChange("")}
            type="button"
          >
            <X size={14} />
          </button>
        ) : null}
      </div>
      <PopoverContent
        align="start"
        className="w-auto p-1"
        /* Nas landings o calendario abre dentro da caixa do site (`.bzlp`):
           no body ficava fora do tema escuro e saia branco. No portal nao ha
           `.bzlp` e continua a ir para o body. */
        container={caixaRef.current?.closest<HTMLElement>(".bzlp")}
        onCloseAutoFocus={(e) => {
          if (!escolheu.current || !depoisDeEscolher) return;
          escolheu.current = false;
          e.preventDefault();
          depoisDeEscolher();
        }}
      >
        <Calendar
          className="[--cell-size:--spacing(9)]"
          disabled={desactivados.length ? desactivados : undefined}
          locale={locale === "pt" ? pt : enGB}
          mode="single"
          onSelect={(d) => {
            onChange(d ? paraIso(d) : "");
            escolheu.current = Boolean(d);
            setAberto(false);
          }}
          selected={escolhida}
          startMonth={minimo}
          // Explicito, e nao herdado da locale: em Mocambique e em Portugal a
          // semana comeca a segunda, e o calendario estava a abrir ao domingo.
          weekStartsOn={1}
        />
      </PopoverContent>
    </Popover>
  );
}
