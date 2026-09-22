import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown, Moon, Palette, RotateCcw, Sun, Upload, X } from "lucide-react";
import { useUi } from "../ui/UiPreferences";
import { useGestorDeTema } from "./useGestorDeTema";
import { CORES_DE_MARCA, RAIOS, type TemaDeCor } from "./tipos";
import { tpmTurPreset } from "./presets/tpm-tur";
import "./customizer.css";

/** Os 51 presets do template sao ~140KB de dados. Carregam-se so quando o
 *  painel abre — nao ha razao para os pedir a quem nunca o abre. (No arranque,
 *  a reaplicacao usa os estilos ja resolvidos em localStorage.) */
async function carregarPresets(): Promise<TemaDeCor[]> {
  const [shadcn, tweakcn] = await Promise.all([
    import("./presets/shadcn"),
    import("./presets/tweakcn"),
  ]);
  const converter = (mapa: Record<string, { label?: string; styles: { light: Record<string, string>; dark: Record<string, string> } }>) =>
    Object.entries(mapa).map(([chave, preset]) => ({
      nome: preset.label || chave,
      valor: chave,
      preset,
    }));
  return [
    { nome: "TPM-TUR", valor: "tpm-tur", preset: tpmTurPreset },
    ...converter(shadcn.shadcnThemePresets),
    ...converter(tweakcn.tweakcnPresets),
  ];
}

/** As quatro cores que resumem um tema, como no selector do template:
 *  accao, secundaria, subtil e fundo — sempre do lado claro, que e onde
 *  as diferencas entre presets se veem melhor. */
function pontosDoTema(t: TemaDeCor): string[] {
  const s = t.preset.styles.light;
  return [s.primary, s.secondary, s.accent, s.muted].filter(Boolean);
}

export default function ThemeCustomizer() {
  const [aberto, setAberto] = useState(false);
  const [temas, setTemas] = useState<TemaDeCor[]>([]);
  const [aCarregar, setACarregar] = useState(false);
  const [importado, setImportado] = useState("");
  const [erroImport, setErroImport] = useState("");
  const g = useGestorDeTema();
  const { toggleTheme } = useUi();

  useEffect(() => {
    if (!aberto || temas.length > 0 || aCarregar) return;
    setACarregar(true);
    carregarPresets()
      .then(setTemas)
      .finally(() => setACarregar(false));
  }, [aberto, temas.length, aCarregar]);

  // O preset guardado volta a aplicar-se no arranque e a cada troca
  // claro/escuro — com o painel fechado ou aberto. Cada preset traz dois
  // conjuntos de valores e so um deles pode estar no <html> de cada vez.
  const restaurar = g.restaurarGuardado;
  useEffect(() => {
    restaurar();
  }, [g.escuro, restaurar]);

  function importar() {
    try {
      const dados = JSON.parse(importado);
      if (!dados.light || !dados.dark) throw new Error("faltam as chaves 'light' e 'dark'");
      g.aplicarImportado(dados);
      setErroImport("");
    } catch (e) {
      setErroImport(e instanceof Error ? e.message : "JSON invalido");
    }
  }

  const temaActual = temas.find((t) => t.valor === g.presetActual);

  return (
    <>
      <button
        className="icon-button"
        type="button"
        aria-label="Personalizar tema"
        title="Personalizar tema"
        onClick={() => setAberto(true)}
      >
        <Palette size={18} />
      </button>

      {aberto && createPortal(
        /* Em portal para o <body>, e nao onde o botao vive: o `.admin-topbar`
         * tem `backdrop-filter`, que cria bloco de contencao. Um
         * `position: fixed` la dentro resolve contra a barra de 70px em vez
         * da janela, e o painel saia com 69px de altura, so o cabecalho. */
        <div className="tc-overlay" onClick={() => setAberto(false)}>
          <aside
            className="tc-painel"
            role="dialog"
            aria-label="Personalizar tema"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="tc-cabeca">
              <div>
                <p className="tc-kicker">Aparência</p>
                <strong>Personalizar tema</strong>
              </div>
              <button className="icon-button" type="button" aria-label="Fechar" onClick={() => setAberto(false)}>
                <X size={18} />
              </button>
            </header>

            <section className="tc-seccao">
              <span className="tc-rotulo" id="tc-tema-rotulo">Tema</span>
              <ListaDeTemas
                temas={temas}
                aCarregar={aCarregar}
                temaActual={temaActual}
                presetActual={g.presetActual}
                aoEscolher={(t) => g.aplicarPreset(t.valor, t.preset)}
              />
              <p className="tc-nota">
                O tema da TPM-TUR é o de origem. Os restantes servem para ver como o
                produto fica noutro operador.
              </p>
            </section>

            <section className="tc-seccao">
              <span className="tc-rotulo">Modo</span>
              <div className="tc-modo" role="group" aria-label="Modo claro ou escuro">
                <button type="button" className={`tc-modo-btn${g.escuro ? "" : " tc-modo-activo"}`}
                  onClick={() => { if (g.escuro) toggleTheme(); }}>
                  <Sun size={15} /> Claro
                </button>
                <button type="button" className={`tc-modo-btn${g.escuro ? " tc-modo-activo" : ""}`}
                  onClick={() => { if (!g.escuro) toggleTheme(); }}>
                  <Moon size={15} /> Escuro
                </button>
              </div>
            </section>

            <section className="tc-seccao">
              <span className="tc-rotulo">Cores de marca</span>
              <div className="tc-cores">
                {CORES_DE_MARCA.map((c) => (
                  <label className="tc-cor" key={c.cssVar}>
                    <input
                      type="color"
                      value={normalizar(g.coresDeMarca[c.cssVar] ?? lerVariavel(c.cssVar))}
                      onChange={(e) => g.mudarCor(c.cssVar, e.target.value)}
                    />
                    <span>{c.nome}</span>
                  </label>
                ))}
              </div>
            </section>

            <section className="tc-seccao">
              <span className="tc-rotulo">Arredondamento</span>
              <div className="tc-raios">
                {RAIOS.map((r) => (
                  <button
                    key={r.valor}
                    type="button"
                    aria-pressed={g.raioActual === r.valor}
                    className={`tc-raio${g.raioActual === r.valor ? " tc-raio-activo" : ""}`}
                    onClick={() => g.aplicarRaio(r.valor)}
                  >
                    {r.nome}
                  </button>
                ))}
              </div>
            </section>

            <section className="tc-seccao">
              <label className="tc-rotulo" htmlFor="tc-import">
                <Upload size={13} /> Importar tema
              </label>
              <textarea
                id="tc-import"
                className="tc-textarea"
                rows={4}
                placeholder='{"light": {"primary": "#087d99"}, "dark": {…}}'
                value={importado}
                onChange={(e) => setImportado(e.target.value)}
              />
              {erroImport && <p className="tc-erro" role="alert">{erroImport}</p>}
              <button className="tc-botao" type="button" onClick={importar} disabled={!importado.trim()}>
                Aplicar
              </button>
            </section>

            <footer className="tc-rodape">
              <button className="tc-botao tc-repor" type="button" onClick={() => {
                g.repor();
                setImportado("");
                setErroImport("");
              }}>
                <RotateCcw size={15} /> Repor TPM-TUR
              </button>
              <p className="tc-nota">
                As alterações ficam neste navegador e não afectam ninguém mais.
              </p>
            </footer>
          </aside>
        </div>,
        document.body,
      )}
    </>
  );
}

/** O <select> nativo nao mostra as cores dos temas — e escolher um tema sem
 *  ver as cores e escolher as cegas. Lista propria: botao com as quatro
 *  cores do tema actual, popover com um tema por linha. */
function ListaDeTemas({ temas, aCarregar, temaActual, presetActual, aoEscolher }: {
  temas: TemaDeCor[];
  aCarregar: boolean;
  temaActual: TemaDeCor | undefined;
  presetActual: string;
  aoEscolher: (t: TemaDeCor) => void;
}) {
  const [listaAberta, setListaAberta] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!listaAberta) return;
    const fora = (e: MouseEvent) => {
      if (!caixa.current?.contains(e.target as Node)) setListaAberta(false);
    };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setListaAberta(false); };
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [listaAberta]);

  const nomeActual = presetActual === "importado" ? "Importado" : (temaActual?.nome ?? "TPM-TUR");
  const pontos = temaActual ? pontosDoTema(temaActual) : pontosDoTema({ nome: "", valor: "tpm-tur", preset: tpmTurPreset });

  return (
    <div className="tc-listbox" ref={caixa}>
      <button
        type="button"
        className="tc-listbox-botao"
        aria-haspopup="listbox"
        aria-expanded={listaAberta}
        onClick={() => !aCarregar && setListaAberta((v) => !v)}
      >
        <span className="tc-pontos" aria-hidden>
          {pontos.map((cor, i) => <i key={i} style={{ background: cor }} />)}
        </span>
        <span className="tc-listbox-nome">{aCarregar ? "A carregar…" : nomeActual}</span>
        <ChevronDown size={15} />
      </button>
      {listaAberta && (
        <ul className="tc-listbox-lista" role="listbox" aria-activedescendant={presetActual}>
          {presetActual === "importado" && (
            <li className="tc-opcao tc-opcao-activa" role="option" aria-selected="true" id="importado">
              <span className="tc-pontos" aria-hidden />
              <span>Importado</span>
              <Check size={14} />
            </li>
          )}
          {temas.map((t) => (
            <li
              key={t.valor}
              id={t.valor}
              role="option"
              aria-selected={t.valor === presetActual}
              className={`tc-opcao${t.valor === presetActual ? " tc-opcao-activa" : ""}`}
              onClick={() => {
                aoEscolher(t);
                setListaAberta(false);
              }}
            >
              <span className="tc-pontos" aria-hidden>
                {pontosDoTema(t).map((cor, i) => <i key={i} style={{ background: cor }} />)}
              </span>
              <span>{t.nome}</span>
              {t.valor === presetActual && <Check size={14} />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function lerVariavel(cssVar: string) {
  if (typeof window === "undefined") return "#000000";
  return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
}

/** O <input type="color"> so aceita #rrggbb. Os presets do template usam
 *  oklch(), que ele nao entende — nesse caso mostra-se preto em vez de
 *  rebentar, e a cor real continua a ser a do preset ate alguem lhe mexer. */
function normalizar(valor: string) {
  return /^#[0-9a-f]{6}$/i.test(valor) ? valor : "#000000";
}
