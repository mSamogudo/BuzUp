import { t, type Locale } from "./i18n";

/**
 * O que se mostra ao utilizador quando alguma coisa falha.
 *
 * O portal fazia `mensagemDeErro(err, lc)` em 55 sítios.
 * Isso punha no ecrã o que quer que viesse do servidor ou do browser — desde
 * `Failed to fetch` até um despejo do Django — e, quando não vinha nada, a
 * palavra "Erro" sozinha, que não diz o que aconteceu nem o que fazer.
 *
 * A regra aqui é simples: **a mensagem do servidor passa; a do browser não.**
 * O backend responde coisas concretas e accionáveis ("Esta partida vai no
 * sentido contrário ao percurso escolhido"), e essas valem mais do que
 * qualquer texto genérico que se escrevesse aqui. O que não presta são as
 * falhas de transporte, e essas passam a ser ditas por palavras.
 */
export function mensagemDeErro(err: unknown, lc: Locale): string {
  const bruto = err instanceof Error ? err.message : String(err ?? "");
  const texto = bruto.trim();

  if (!texto) return t(lc, "errUnknown");

  // Falhas de rede do `fetch`. A mensagem varia com o browser e nenhuma delas
  // é para ler: "Failed to fetch", "NetworkError when attempting to fetch
  // resource", "Load failed".
  const rede = /failed to fetch|networkerror|load failed|network request failed/i;
  if (rede.test(texto)) return t(lc, "errNetwork");

  // `Erro 500`, `Falha ao descarregar (502)` — códigos que o utilizador não
  // pode resolver e que só assustam.
  const servidor = /\b5\d{2}\b/.test(texto) && texto.length < 40;
  if (servidor) return t(lc, "errServer");

  // Restos de JSON ou de stack: nunca chegaram a ser uma frase.
  if (/^[[{]/.test(texto) || texto.includes("\n    at ")) return t(lc, "errUnknown");

  return texto;
}
