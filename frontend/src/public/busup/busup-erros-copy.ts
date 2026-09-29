import type { Lang } from "../landing/useLandingPrefs";

/* Textos dos ecrãs de erro — `Erros BusUp.dc.html`, verbatim.
 *
 * Seis estados: 404, 401, 403, 500, 503 e sem ligação. Cada um diz o que
 * aconteceu, SE HOUVE COBRANÇA, e o que fazer a seguir. É essa segunda parte
 * que torna estes ecrãs úteis num sistema de bilhética: quem vê um 500 a meio
 * de um pagamento quer saber, antes de tudo, se lhe tiraram o dinheiro.
 */

export type Tom = "info" | "aviso" | "mau";
export type ChaveErro = "404" | "401" | "403" | "500" | "503" | "offline";

export type Erro = {
  chave: ChaveErro;
  codigo: string;
  tom: Tom;
  pilula: string;
  titulo: string;
  lead: string;
  cta1: string;
  cta2: string;
  pistas: { k: string; v: string }[];
  /* A referência do protótipo é uma AMOSTRA. O que varia — o caminho, a hora,
     o número do incidente — entra em runtime; ver `referencia()` na página. */
  ref: string;
};

export type CopyErros = {
  help: string;
  statusPage: string;
  poweredBy: string;
  erros: Erro[];
};

const p = (k: string, v: string) => ({ k, v });

const PT: CopyErros = {
  help: "Ajuda",
  statusPage: "Estado dos serviços",
  poweredBy: "Desenvolvido por",
  erros: [
    {
      chave: "404", codigo: "404", tom: "info", pilula: "Página não encontrada",
      titulo: "Esta página mudou de sítio.",
      lead: "O endereço que abriu já não existe ou foi escrito com um erro. As páginas principais continuam todas disponíveis.",
      cta1: "Voltar ao início", cta2: "Comprar bilhete",
      pistas: [
        p("Percursos e horários", "Consulte as partidas do dia na página de compra."),
        p("Preços", "A tabela por tipo de operação está na página de preços."),
        p("Falar connosco", "sales@updigital.co.mz · dias úteis, 08h–17h."),
      ],
      ref: "ref. 404",
    },
    {
      chave: "401", codigo: "401", tom: "info", pilula: "Sessão terminada",
      titulo: "A sua sessão expirou.",
      lead: "Por segurança, terminamos a sessão depois de um período sem actividade. Volte a entrar para continuar de onde estava.",
      cta1: "Entrar de novo", cta2: "Ir para o início",
      pistas: [
        p("Nada se perdeu", "O trabalho por gravar fica no dispositivo até voltar a entrar."),
        p("Acesso por SMS", "Passageiros entram com o código enviado por SMS."),
        p("Senha esquecida", "Peça a reposição no ecrã de entrada."),
      ],
      ref: "ref. 401",
    },
    {
      chave: "403", codigo: "403", tom: "aviso", pilula: "Sem permissão",
      titulo: "A sua conta não tem acesso a esta área.",
      lead: "O acesso é definido pelo papel da conta. Se precisa desta área para o seu trabalho, peça ao administrador da operação.",
      cta1: "Voltar ao painel", cta2: "Pedir acesso",
      pistas: [
        p("O que vê", "Cada papel abre apenas as áreas do seu trabalho."),
        p("Quem autoriza", "O administrador da operação altera papéis no portal."),
        p("Registo", "Tentativas de acesso ficam na auditoria."),
      ],
      ref: "ref. 403",
    },
    {
      chave: "500", codigo: "500", tom: "mau", pilula: "Erro do servidor",
      titulo: "Alguma coisa falhou do nosso lado.",
      lead: "O pedido não chegou a ser concluído e nada foi cobrado. A equipa já recebeu o alerta com a referência abaixo.",
      cta1: "Tentar de novo", cta2: "Falar com o suporte",
      pistas: [
        p("Pagamentos", "Nenhum valor é cobrado quando o pedido falha."),
        p("Bilhetes emitidos", "Continuam válidos e disponíveis no telemóvel."),
        p("Referência", "Indique-a ao suporte para acelerar a resposta."),
      ],
      ref: "ref. 500",
    },
    {
      chave: "503", codigo: "503", tom: "aviso", pilula: "Manutenção programada",
      titulo: "Estamos a actualizar a plataforma.",
      lead: "A janela de manutenção termina às 06h00. A validação a bordo continua a funcionar sem ligação e sincroniza quando voltarmos.",
      cta1: "Ver estado dos serviços", cta2: "Avisar-me quando voltar",
      pistas: [
        p("Validação a bordo", "A app POS valida offline durante a janela."),
        p("Venda online", "Fica indisponível até às 06h00."),
        p("Duração prevista", "40 minutos · 05h20 às 06h00 (CAT)."),
      ],
      ref: "ref. 503 · janela 05h20–06h00 CAT",
    },
    {
      chave: "offline", codigo: "⚡", tom: "mau", pilula: "Sem ligação",
      titulo: "O dispositivo está sem Internet.",
      lead: "Continua a validar bilhetes offline: as leituras ficam guardadas no aparelho e sobem assim que houver rede.",
      cta1: "Tentar ligar de novo", cta2: "Continuar offline",
      pistas: [
        p("Validações guardadas", "18 leituras por sincronizar neste aparelho."),
        p("Venda", "A venda de bilhetes precisa de rede."),
        p("Última sincronização", "hoje, 09h41."),
      ],
      ref: "ref. net",
    },
  ],
};

const EN: CopyErros = {
  help: "Help",
  statusPage: "Service status",
  poweredBy: "Powered by",
  erros: [
    {
      chave: "404", codigo: "404", tom: "info", pilula: "Page not found",
      titulo: "This page has moved.",
      lead: "The address you opened no longer exists or was mistyped. Every main page is still available.",
      cta1: "Back to home", cta2: "Buy a ticket",
      pistas: [
        p("Routes and times", "Check today's departures on the purchase page."),
        p("Pricing", "The table by operation type is on the pricing page."),
        p("Talk to us", "sales@updigital.co.mz · weekdays, 08:00–17:00."),
      ],
      ref: "ref. 404",
    },
    {
      chave: "401", codigo: "401", tom: "info", pilula: "Session ended",
      titulo: "Your session has expired.",
      lead: "For safety we end the session after a period without activity. Sign in again to pick up where you were.",
      cta1: "Sign in again", cta2: "Go to home",
      pistas: [
        p("Nothing was lost", "Unsaved work stays on the device until you sign in."),
        p("SMS access", "Passengers sign in with the code sent by SMS."),
        p("Forgot password", "Request a reset on the sign-in screen."),
      ],
      ref: "ref. 401",
    },
    {
      chave: "403", codigo: "403", tom: "aviso", pilula: "No permission",
      titulo: "Your account cannot open this area.",
      lead: "Access follows the account role. If you need this area for your work, ask the operation's administrator.",
      cta1: "Back to dashboard", cta2: "Request access",
      pistas: [
        p("What you see", "Each role opens only the areas of its work."),
        p("Who authorises", "The administrator changes roles in the portal."),
        p("Record", "Access attempts are kept in the audit log."),
      ],
      ref: "ref. 403",
    },
    {
      chave: "500", codigo: "500", tom: "mau", pilula: "Server error",
      titulo: "Something failed on our side.",
      lead: "The request never completed and nothing was charged. The team already has the alert with the reference below.",
      cta1: "Try again", cta2: "Contact support",
      pistas: [
        p("Payments", "No amount is charged when a request fails."),
        p("Issued tickets", "Remain valid and available on the phone."),
        p("Reference", "Give it to support to speed up the answer."),
      ],
      ref: "ref. 500",
    },
    {
      chave: "503", codigo: "503", tom: "aviso", pilula: "Scheduled maintenance",
      titulo: "We are updating the platform.",
      lead: "The maintenance window ends at 06:00. Onboard validation keeps working offline and syncs when we are back.",
      cta1: "See service status", cta2: "Notify me when back",
      pistas: [
        p("Onboard validation", "The POS app validates offline during the window."),
        p("Online sales", "Unavailable until 06:00."),
        p("Expected duration", "40 minutes · 05:20 to 06:00 (CAT)."),
      ],
      ref: "ref. 503 · window 05:20–06:00 CAT",
    },
    {
      chave: "offline", codigo: "⚡", tom: "mau", pilula: "No connection",
      titulo: "This device has no Internet.",
      lead: "Keep validating offline: scans are stored on the device and upload as soon as there is a network.",
      cta1: "Try to reconnect", cta2: "Continue offline",
      pistas: [
        p("Stored validations", "18 scans waiting to sync on this device."),
        p("Sales", "Selling tickets needs a network."),
        p("Last sync", "today, 09:41."),
      ],
      ref: "ref. net",
    },
  ],
};

export function copyErros(lang: Lang): CopyErros {
  return lang === "en" ? EN : PT;
}

export function erro(lang: Lang, chave: ChaveErro): Erro {
  const c = copyErros(lang);
  return c.erros.find((e) => e.chave === chave) ?? c.erros[0];
}
