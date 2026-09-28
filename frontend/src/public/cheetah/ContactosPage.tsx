import { Building2, Mail, Ticket } from "lucide-react";
import CheRevela from "./CheRevela";
import FormularioPedido from "../comum/FormularioPedido";
import CheetahPagina, {
  CheetahIntro, EMAIL_GERAL, EMAIL_RESERVAS, MORADA, useCheetahMeta,
} from "./CheetahChrome";
import { useCheetahCopy } from "./cheetah-copy";

/* Contactos. A empresa publica DOIS endereços de email e nenhum telefone — é o
 * que está no site oficial, e não se inventa um número. Por isso o formulário
 * partilhado recebe `telefone` vazio: a propriedade é opcional precisamente
 * para este caso.
 *
 * O formulário fica na coluna larga e os cartões na estreita. Quem chega a
 * esta página quer escrever, e não ler moradas — a acção vem primeiro.
 */

export default function ContactosPage() {
  const { t } = useCheetahCopy();
  const c = t.contactos;

  useCheetahMeta(c.meta.titulo, c.meta.descricao);

  return (
    <CheetahPagina activa="/cheetah-express/contactos">
      <CheetahIntro migalha={c.migalha} titulo={c.titulo} descricao={c.descricao} />

      <section className="bzlp-sec">
        <div className="bzlp-wrap">
          <div className="che-contactos">
            <CheRevela>
              <FormularioPedido
                textos={c.form}
                email={EMAIL_RESERVAS}
                prefixoAssunto="Cheetah Express"
                dicaTelefone="+258 84 000 0000"
              />
            </CheRevela>

            <CheRevela ordem={1}>
              <div className="che-contacto-cartoes">
                <div className="che-contacto-cartao">
                  <span className="che-contacto-ico"><Ticket size={20} aria-hidden /></span>
                  <h2>{c.cartoes.reservas.t}</h2>
                  <p>{c.cartoes.reservas.p}</p>
                  <a href={`mailto:${EMAIL_RESERVAS}`}>{EMAIL_RESERVAS}</a>
                </div>

                <div className="che-contacto-cartao">
                  <span className="che-contacto-ico"><Mail size={20} aria-hidden /></span>
                  <h2>{c.cartoes.geral.t}</h2>
                  <p>{c.cartoes.geral.p}</p>
                  <a href={`mailto:${EMAIL_GERAL}`}>{EMAIL_GERAL}</a>
                </div>

                <div className="che-contacto-cartao">
                  <span className="che-contacto-ico"><Building2 size={20} aria-hidden /></span>
                  <h2>{c.cartoes.escritorio.t}</h2>
                  <p>{c.cartoes.escritorio.p}</p>
                  <span>{MORADA}</span>
                </div>
              </div>
            </CheRevela>
          </div>
        </div>
      </section>
    </CheetahPagina>
  );
}
