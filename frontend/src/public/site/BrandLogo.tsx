type BrandLogoProps = {
  tone?: "onLight" | "onDark";
};

export function BrandLogo({ tone = "onLight" }: BrandLogoProps) {
  const src =
    tone === "onDark"
      ? "/assets/buzup-logo/buzup-logo.png"
      : "/assets/buzup-logo/buzup-logo-dark.png";

  return <img className="brand-logo" src={src} alt="BusUp" />;
}
