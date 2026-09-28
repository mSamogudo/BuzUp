import { useLocation } from "react-router-dom";
import { useLandingPrefs } from "../public/landing/useLandingPrefs";

/* O ecrã de arranque, vestido com a marca de quem está a entrar.
 *
 * Havia um só, e dizia "BU / BusUp" em texto. Quem abria o site da TPM-TUR ou
 * da Cheetah Express via a marca do FORNECEDOR antes de ver a do operador —
 * exactamente ao contrário do que deve ser. Agora a rota decide.
 *
 * A TINTA DE CADA LOGÓTIPO SAI DE MEDIÇÃO, e não do nome do ficheiro. Nesta
 * base os nomes enganam, e está documentado noutros sítios: medi a luminância
 * média da tinta de cada um.
 *   busup/logo-dark.png ............ 181, tinta clara → vai sobre ESCURO
 *   busup/logo-light.png ............ 42, tinta escura → vai sobre CLARO
 *   up_digital_light.png ........... 206, tinta clara → vai sobre ESCURO
 *   up_digital_dark.png ............. 23, tinta escura → vai sobre CLARO
 *   tpm_dark.png ................... 176, tinta clara → vai sobre ESCURO
 *   cheetah-logo.png ................ 85, tinta escura → vai sobre CLARO
 * Ou seja: na BusUp "dark" quer dizer "para fundo escuro" e na UpDigital
 * "light" quer dizer "tinta clara". Trocá-las dá um logótipo invisível.
 *
 * A chapa da Cheetah é AMARELA, ao contrário das outras duas — por isso é a
 * única que leva as variantes de tinta escura em todos os três logótipos.
 */

type Marca = {
  id: "busup" | "tpm" | "cheetah";
  /** O logótipo grande, o de quem recebe a visita. */
  logo: { src: string; w: number; h: number; alt: string };
  /** O da BusUp, quando o operador não É a BusUp. */
  sistema: { src: string; w: number; h: number } | null;
  updigital: { src: string; w: number; h: number };
};

const BUSUP: Marca = {
  id: "busup",
  logo: { src: "/assets/busup/logo-dark.png", w: 444, h: 165, alt: "BusUp" },
  sistema: null, // seria o seu próprio logótipo duas vezes
  updigital: { src: "/assets/up-digital-logo/up_digital_light.png", w: 447, h: 180 },
};

const TPM: Marca = {
  id: "tpm",
  /* O mesmo ficheiro que a barra e o rodapé usam: 720x180 em WebP sem perdas,
     43KB contra os 285KB do PNG de origem. Um só ficheiro para as três
     utilizações significa também que o do arranque já está em cache quando a
     barra aparece. */
  logo: { src: "/assets/tpm-tur-logo/tpm_dark.webp", w: 720, h: 180, alt: "TPM-TUR, S.A." },
  sistema: { src: "/assets/busup/logo-dark.png", w: 444, h: 165 },
  updigital: { src: "/assets/up-digital-logo/up_digital_light.png", w: 447, h: 180 },
};

const CHEETAH: Marca = {
  id: "cheetah",
  logo: { src: "/assets/cheetah-logo/cheetah-logo.png", w: 750, h: 230, alt: "Cheetah Express" },
  sistema: { src: "/assets/busup/logo-light.png", w: 444, h: 165 },
  updigital: { src: "/assets/up-digital-logo/up_digital_dark.png", w: 484, h: 180 },
};

/** Quem está a entrar, lido da rota. Tudo o que não é de um operador é BusUp —
 *  o portal de gestão, a compra, o login. */
function marcaDaRota(caminho: string): Marca {
  if (caminho.startsWith("/tpm-tur")) return TPM;
  if (caminho.startsWith("/cheetah-express")) return CHEETAH;
  return BUSUP;
}

const TEXTOS = {
  pt: { tecnologia: "Tecnologia", desenvolvidoPor: "Desenvolvido por", aCarregar: "A carregar" },
  en: { tecnologia: "Powered by", desenvolvidoPor: "Built by", aCarregar: "Loading" },
};

/**
 * O ecrã de arranque completo: a marca de quem recebe, e em baixo quem põe a
 * tecnologia e quem a fez.
 *
 * Só no ARRANQUE. Entre páginas do mesmo site o código chega em dezenas de
 * milissegundos, e apresentar três logótipos nesse tempo faz uma espera curta
 * parecer longa — para isso existe o `SplashLeve` aqui ao lado.
 */
export default function SplashScreen() {
  const marca = marcaDaRota(useLocation().pathname);
  const { lang } = useLandingPrefs();
  const t = TEXTOS[lang] ?? TEXTOS.pt;

  return (
    /* `role="status"` e `aria-live`: quem não vê o ecrã fica na mesma a saber
       que a aplicação está a carregar, em vez de ouvir três nomes de empresa
       sem contexto. */
    <div className={`splash-screen splash-${marca.id}`} role="status" aria-live="polite">
      <span className="sr-only">{t.aCarregar}…</span>

      <img
        className="splash-marca"
        src={marca.logo.src}
        alt={marca.logo.alt}
        width={marca.logo.w}
        height={marca.logo.h}
        /* `width`/`height` reais do ficheiro reservam o espaço: sem eles a
           chapa saltava quando a imagem chegasse. */
        decoding="async"
      />

      <div className="splash-spinner" aria-hidden />

      <div className="splash-creditos">
        {marca.sistema && (
          <>
            <span>{t.tecnologia}</span>
            <img src={marca.sistema.src} alt="BusUp" width={marca.sistema.w} height={marca.sistema.h} />
            <span className="splash-creditos-sep" aria-hidden>·</span>
          </>
        )}
        <span>{t.desenvolvidoPor}</span>
        <img src={marca.updigital.src} alt="UpDigital, Limitada"
          width={marca.updigital.w} height={marca.updigital.h} />
      </div>
    </div>
  );
}

/**
 * O ecrã de espera entre páginas: a chapa da marca e o indicador, e mais nada.
 *
 * É a mesma cor de quem se está a visitar, para a transição não piscar de
 * cor — mas sem a apresentação, que já foi feita ao entrar.
 */
export function SplashLeve() {
  const marca = marcaDaRota(useLocation().pathname);
  const { lang } = useLandingPrefs();
  const t = TEXTOS[lang] ?? TEXTOS.pt;
  return (
    <div className={`splash-screen splash-leve splash-${marca.id}`} role="status" aria-live="polite">
      <span className="sr-only">{t.aCarregar}…</span>
      <div className="splash-spinner" aria-hidden />
    </div>
  );
}
