import upDigitalLight from "../assets/up-digital-logo/up_digital_light.png";

export default function SplashScreen() {
  return (
    <div className="splash-screen">
      <div className="splash-orb splash-orb--a" />
      <div className="splash-orb splash-orb--b" />

      <div className="splash-stage">
        <div className="splash-brand">
          <img
            className="splash-wordmark"
            src="/assets/buzup-logo/buzup-logo.png"
            alt="BusUp"
          />
        </div>

        <div className="splash-dots" role="status" aria-label="A carregar">
          <span />
          <span />
          <span />
        </div>

        <div className="splash-credit">
          <span className="splash-credit-by">Desenvolvido por</span>
          <span className="splash-credit-sep" />
          <img
            className="splash-credit-brand"
            src={upDigitalLight}
            alt="UpDigital Limitada"
          />
        </div>
      </div>
    </div>
  );
}
