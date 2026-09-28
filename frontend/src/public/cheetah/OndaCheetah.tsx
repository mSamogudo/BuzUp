/**
 * A onda que separa a chapa da marca do conteúdo — a assinatura do site
 * oficial da Cheetah Express.
 *
 * NÃO É UMA CURVA, SÃO TRÊS. A primeira versão que escrevi tinha um caminho
 * só e lia-se como um recorte; o original empilha três, dois deles a 33% de
 * opacidade e o da frente opaco, cada um a arrancar de uma altura diferente.
 * É essa sobreposição que faz a coisa ondular em vez de simplesmente curvar.
 *
 * Os caminhos são os do site oficial, com a geometria intacta: `viewBox`
 * de 240x24, que `preserveAspectRatio="none"` estica à largura da página.
 *
 * AS TRÊS CAMADAS MOVEM-SE A RITMOS DIFERENTES — 19s, 15s e 23s, números
 * primos entre si de propósito. Com a mesma duração as três deslizavam em
 * bloco e via-se um recorte a abanar; desencontradas, o perfil da onda muda
 * de forma ao longo do tempo e nunca se repete à vista. É daí que vem o
 * efeito ondulado, e não da curva em si.
 */
export default function OndaCheetah({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`che-onda ${className}`.trim()}
      viewBox="0 0 240 24"
      preserveAspectRatio="none"
      aria-hidden
      focusable="false"
    >
      <path className="che-onda-tras" d="M240,24V0c-51.797,0-69.883,13.18-94.707,15.59c-24.691,2.4-43.872-1.17-63.765-1.08c-19.17,0.1-31.196,3.65-51.309,6.58C15.552,23.21,4.321,22.471,0,22.01V24H240z" />
      <path className="che-onda-meio" d="M240,24V2.21c-51.797,0-69.883,11.96-94.707,14.16c-24.691,2.149-43.872-1.08-63.765-1.021c-19.17,0.069-31.196,3.311-51.309,5.971C15.552,23.23,4.321,22.58,0,22.189V24h239.766H240z" />
      <path className="che-onda-frente" d="M240,24V3.72c-51.797,0-69.883,11.64-94.707,14.021c-24.691,2.359-43.872-3.25-63.765-3.17c-19.17,0.109-31.196,3.6-51.309,6.529C15.552,23.209,4.321,22.47,0,22.029V24H240z" />
    </svg>
  );
}
