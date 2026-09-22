/** Formato de preset do template shadcn: um mapa de variaveis CSS por tema.
 *  As chaves vao sem `--` (`primary`, `sidebar-foreground`, ...). */
export interface ThemePreset {
  label?: string;
  /** Metadados que o tweakcn traz e nos nao usamos — ficam para o ficheiro
   *  continuar a ser uma copia directa, facil de actualizar. */
  createdAt?: string;
  styles: {
    light: Record<string, string>;
    dark: Record<string, string>;
  };
}

export interface TemaDeCor {
  nome: string;
  valor: string;
  preset: ThemePreset;
}

/** As cores de marca que o customizador deixa mexer a mao. Sao as que
 *  distinguem um operador do outro; o resto deriva delas ou e semantico. */
export const CORES_DE_MARCA = [
  { nome: "Acção", cssVar: "--primary" },
  { nome: "Texto sobre a acção", cssVar: "--primary-foreground" },
  { nome: "Barra lateral", cssVar: "--sidebar" },
  { nome: "Texto da barra", cssVar: "--sidebar-foreground" },
  { nome: "Atenção", cssVar: "--warning" },
  { nome: "Sucesso", cssVar: "--success" },
] as const;

export const RAIOS = [
  { nome: "0", valor: "0rem" },
  { nome: "0,25", valor: "0.25rem" },
  { nome: "0,5", valor: "0.5rem" },
  { nome: "0,75", valor: "0.75rem" },
  { nome: "1,0", valor: "1rem" },
] as const;
