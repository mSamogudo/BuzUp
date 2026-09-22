import { Children, isValidElement, useId, type ReactNode } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Campo de escolha, por dentro o Select do shadcn.
 *
 *  Aceita `<option>` como filhos de proposito. Dos 65 selects da aplicacao,
 *  33 constroem as opcoes com `.map()` sobre dados carregados e 2 misturam
 *  opcoes fixas com dinamicas; uma prop `options` declarativa nao cobria
 *  esses casos sem reescrever cada sitio de chamada. Assim o JSX das opcoes
 *  fica como estava e so a etiqueta de fora muda.
 *
 *  Duas diferencas do `<select>` nativo que obrigam a tratamento:
 *
 *  O Radix reserva a string vazia para "sem seleccao" e rejeita um item com
 *  `value=""`. Mas `<option value="">Todos</option>` e o modo normal de
 *  limpar um filtro aqui, e tem de continuar a ser escolhivel — dai o
 *  sentinela, traduzido nas duas direccoes.
 *
 *  E o gatilho do Radix e um `<button>`, que nao e rotulavel: um `<label>`
 *  por fora deixaria de lhe dar nome acessivel. Por isso a etiqueta e
 *  explicita, ligada por `htmlFor`. */

const VAZIO = "__vazio__";

type OpcaoProps = { value?: string | number; children?: ReactNode; disabled?: boolean };

/** `<option>` -> `SelectItem`, atravessando as listas que o `.map()` devolve. */
function paraItens(filhos: ReactNode): ReactNode[] {
  return Children.toArray(filhos).flatMap((filho, i) => {
    if (!isValidElement(filho)) return [];
    if (filho.type !== "option") return [filho];
    const { value, children, disabled } = filho.props as OpcaoProps;
    const v = value === undefined || value === "" ? VAZIO : String(value);
    return [
      <SelectItem disabled={disabled} key={filho.key ?? `${v}-${i}`} value={v}>
        {children}
      </SelectItem>,
    ];
  });
}

export function CampoSelect({
  label,
  value,
  onChange,
  children,
  id,
  disabled = false,
  required = false,
  placeholder,
  compacto = false,
  className,
  "aria-label": rotuloAcessivel,
}: {
  label?: ReactNode;
  value: string;
  onChange: (valor: string) => void;
  children: ReactNode;
  id?: string;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
  compacto?: boolean;
  className?: string;
  /** Para filtros de barra, que nao tem etiqueta visivel. */
  "aria-label"?: string;
}) {
  const gerado = useId();
  const idGatilho = id ?? gerado;

  return (
    <div className={className ?? "field"}>
      {label ? <Label htmlFor={idGatilho}>{label}</Label> : null}
      <Select
        disabled={disabled}
        onValueChange={(v) => onChange(v === VAZIO ? "" : v)}
        required={required}
        value={value === "" ? VAZIO : value}
      >
        <SelectTrigger aria-label={rotuloAcessivel} className="w-full" id={idGatilho} size={compacto ? "sm" : "default"}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>{paraItens(children)}</SelectContent>
      </Select>
    </div>
  );
}
