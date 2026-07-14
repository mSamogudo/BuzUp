type BrandLogoProps = {
  /**
   * "onLight" / "onDark" pin a fixed wordmark (use when the surface tone is
   * fixed regardless of theme, e.g. the navy footer -> "onDark").
   * "auto" renders both and swaps by the active theme via CSS — use on
   * theme-reactive surfaces (nav, drawer) so the wordmark never disappears
   * against a dark hero in dark mode.
   */
  tone?: "onLight" | "onDark" | "auto";
};

const WHITE = "/assets/buzup-logo/buzup-logo.png"; // white wordmark (for dark surfaces)
const NAVY = "/assets/buzup-logo/buzup-logo-dark.png"; // navy wordmark (for light surfaces)

export function BrandLogo({ tone = "onLight" }: BrandLogoProps) {
  if (tone === "auto") {
    return (
      <span className="brand-logo-swap">
        <img className="brand-logo logo-light" src={NAVY} alt="BusUp" />
        <img className="brand-logo logo-dark" src={WHITE} alt="" aria-hidden="true" />
      </span>
    );
  }
  return <img className="brand-logo" src={tone === "onDark" ? WHITE : NAVY} alt="BusUp" />;
}
