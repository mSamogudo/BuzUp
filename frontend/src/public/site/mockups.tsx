/**
 * Maquetas decorativas do site público.
 *
 * São as imagens do produto desenhadas nos protótipos do handoff
 * (`docs/design-handoff/design/Landing BusUp - Ceu.dc.html`): a pré-visualização
 * do portal por baixo do herói e as miniaturas dentro dos cartões de recursos.
 *
 * Não têm dados reais nem interacção — são ilustração. Ficam fora do CMS de
 * propósito: o que o editor mexe é a cópia, não o desenho destas peças. Por
 * serem decorativas, ficam todas com `aria-hidden`.
 */
import marca from "../../assets/busup/busup-mark.png";

const LUGARES_OCUPADOS = new Set([
  0, 1, 2, 4, 5, 7, 8, 9, 11, 12, 13, 15, 16, 18, 19, 20, 22, 23, 25, 26, 28, 30,
]);

/** Pré-visualização do portal, cortada em baixo, por baixo do herói. */
export function PortalPreview() {
  return (
    <div aria-hidden="true" className="bzs-dash-clip">
      <div className="bzs-dash">
        <div className="bzs-dash-top">
          <div className="bzs-dash-brand">
            <img alt="" src={marca} />
            <b>BusUp</b>
          </div>
          <div className="bzs-dash-tabs">
            <span className="is-on">Dashboard</span>
            <span>Rotas</span>
            <span>Viaturas</span>
            <span>Viagens</span>
            <span>Cartões</span>
            <span>Relatórios</span>
            <span>Auditoria</span>
          </div>
          <div className="bzs-dash-top-right">
            <span className="bzs-dash-search">Pesquisar…</span>
            <span className="bzs-dash-avatar">AM</span>
          </div>
        </div>

        <div className="bzs-dash-body">
          <div className="bzs-dash-head">
            <b>Painel de operação</b>
            <span className="bzs-dash-live">
              <i />
              Ao vivo
            </span>
            <div className="bzs-dash-filters">
              <span>Hoje</span>
              <span>Todas as rotas</span>
              <span>Exportar</span>
            </div>
          </div>

          <div className="bzs-dash-kpis">
            <div className="bzs-dash-kpi">
              <small>Receita hoje</small>
              <b>
                13 300 <span>MZN</span>
              </b>
            </div>
            <div className="bzs-dash-kpi">
              <small>Bilhetes validados</small>
              <b>140</b>
            </div>
            <div className="bzs-dash-kpi">
              <small>Ocupação</small>
              <b>
                69<span>%</span>
              </b>
              <span className="bzs-dash-bar">
                <i style={{ width: "69%" }} />
              </span>
            </div>
            <div className="bzs-dash-kpi">
              <small>Viagens activas</small>
              <b>12</b>
            </div>
          </div>

          <div className="bzs-dash-split">
            <div className="bzs-dash-panel">
              <div className="bzs-dash-panel-head">
                <b>Validações recentes</b>
                <span>últimos 30 min</span>
              </div>
              <div className="bzs-dash-rows">
                {[
                  ["L5 · Baixa — Aeroporto", "84 123 4567"],
                  ["L2 · Museu — Costa do Sol", "86 998 1122"],
                  ["L6 · Junta — Marracuene", "85 447 9080"],
                  ["L5 · Baixa — Aeroporto", "87 210 3345"],
                ].map(([rota, telefone], i) => (
                  <div className="bzs-dash-row" key={i}>
                    <span>{rota}</span>
                    <span className="bzs-dash-num">{telefone}</span>
                    <span className="bzs-dash-ok">validado</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bzs-dash-panel">
              <b className="bzs-dash-plate">ABC-123-MP</b>
              <small className="bzs-dash-sub">32 lugares · 22 ocupados</small>
              <div className="bzs-dash-seats">
                {Array.from({ length: 32 }, (_, i) => (
                  <i className={LUGARES_OCUPADOS.has(i) ? "is-taken" : undefined} key={i} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Miniatura do cartão "Venda em três canais": comprar bilhete, passo 1 de 3. */
export function MockCompra() {
  return (
    <div aria-hidden="true" className="bzs-mock">
      <div className="bzs-mock-head">
        <b>Comprar bilhete</b>
        <span className="bzs-mock-step">1 / 3</span>
      </div>
      <span className="bzs-mock-field">
        Maputo — Beira<i>›</i>
      </span>
      <span className="bzs-mock-field">
        06:30 · Lugar 14<i>›</i>
      </span>
      <div className="bzs-mock-pay">
        <span className="is-on">M-Pesa</span>
        <span>e-Mola</span>
      </div>
      <span className="bzs-mock-cta">Pagar 850 MZN</span>
    </div>
  );
}

/** Miniatura do cartão "Validação a bordo": quatro decisões seguidas. */
export function MockValidacao() {
  const linhas: [string, string][] = [
    ["ok", "Bilhete QR · aceite"],
    ["ok", "Cartão NFC · aceite"],
    ["warn", "Saldo insuficiente"],
    ["bad", "Bilhete já usado"],
  ];
  return (
    <div aria-hidden="true" className="bzs-mock">
      <div className="bzs-mock-head">
        <b>Validação a bordo</b>
        <span className="bzs-mock-live">
          <i />
          POS ligado
        </span>
      </div>
      <div className="bzs-mock-list">
        {linhas.map(([tom, texto], i) => (
          <span className={`bzs-mock-line bzs-mock-line-${tom}`} key={i}>
            <i />
            {texto}
          </span>
        ))}
      </div>
      <small className="bzs-mock-note">Pacote especial › saldo normal › nega</small>
    </div>
  );
}

/** Miniatura do cartão "Cartões físicos e digitais". */
export function MockCartoes() {
  const linhas: [string, string, string][] = [
    ["NFC · 0042 1187", "activo", "ok"],
    ["NFC · 0042 1188", "activo", "ok"],
    ["QR · maria.j", "pendente", "warn"],
    ["NFC · 0042 1190", "bloqueado", "mute"],
  ];
  return (
    <div aria-hidden="true" className="bzs-mock">
      <div className="bzs-mock-tabs">
        <span className="is-on">Físicos</span>
        <span>Digitais</span>
      </div>
      <div className="bzs-mock-list">
        {linhas.map(([nome, estado, tom], i) => (
          <span className="bzs-mock-card-row" key={i}>
            <b>{nome}</b>
            <em className={`bzs-mock-state bzs-mock-state-${tom}`}>{estado}</em>
          </span>
        ))}
      </div>
      <span className="bzs-mock-import">Importar Excel (.xlsx)</span>
    </div>
  );
}

/** Miniatura do cartão "Receita em tempo real". */
export function MockReceita() {
  const barras = [42, 58, 36, 74, 52, 88, 64];
  return (
    <div aria-hidden="true" className="bzs-mock">
      <div className="bzs-mock-head">
        <b className="bzs-mock-quiet">Receita da semana</b>
        <span className="bzs-mock-state bzs-mock-state-ok">reconciliado</span>
      </div>
      <b className="bzs-mock-big">
        412 850 <span>MZN</span>
      </b>
      <div className="bzs-mock-bars">
        {barras.map((h, i) => (
          <i key={i} style={{ height: `${h}%` }} />
        ))}
      </div>
      <div className="bzs-mock-legend">
        <span>M-Pesa 61%</span>
        <span>e-Mola 22%</span>
        <span>Numerário 17%</span>
      </div>
    </div>
  );
}

/** Miniatura do cartão "Frota e rotas no mapa". */
export function MockFrota({ titulo, aviso }: { titulo: string; aviso: string }) {
  const linhas: [string, string, string][] = [
    ["ABC-123-MP · L5", "42 km/h", "num"],
    ["DEF-456-MP · L2", "em rota", "ok"],
    ["GHI-789-MP · L6", "parada", "mute"],
  ];
  return (
    <div aria-hidden="true" className="bzs-mock">
      <div className="bzs-mock-head">
        <b>{titulo}</b>
        <span className="bzs-mock-live">
          <i />
          GPS
        </span>
      </div>
      <div className="bzs-mock-list">
        {linhas.map(([nome, valor, tom], i) => (
          <span className="bzs-mock-card-row" key={i}>
            <b>{nome}</b>
            <em className={`bzs-mock-state bzs-mock-state-${tom}`}>{valor}</em>
          </span>
        ))}
      </div>
      <span className="bzs-mock-map">{aviso}</span>
    </div>
  );
}

/** Miniaturas dos passos do arranque (secção "Começar em três passos"). */
export function MockPasso({
  m1,
  m1cta,
  m2,
  m2a,
  m2b,
}: {
  m1: string;
  m1cta: string;
  m2: string;
  m2a: string;
  m2b: string;
}) {
  return (
    <div aria-hidden="true" className="bzs-step-mocks">
      <div className="bzs-mock bzs-mock-tight">
        <div className="bzs-mock-head">
          <b>{m1}</b>
        </div>
        <span className="bzs-mock-field" />
        <span className="bzs-mock-field" />
        <span className="bzs-mock-cta">{m1cta}</span>
      </div>
      <div className="bzs-mock bzs-mock-tight">
        <div className="bzs-mock-head">
          <b>{m2}</b>
        </div>
        <span className="bzs-mock-card-row">
          <b>{m2a}</b>
          <em className="bzs-mock-state bzs-mock-state-ok">ok</em>
        </span>
        <span className="bzs-mock-card-row">
          <b>{m2b}</b>
          <em className="bzs-mock-state bzs-mock-state-ok">ok</em>
        </span>
      </div>
    </div>
  );
}
