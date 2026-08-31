/**
 * CMS 3.3 — Biblioteca de media.
 *
 * Grelha de cartões com miniatura, nome, dimensões, peso e "usado em N
 * páginas". Carregamento por arrastar. Detalhe com alt por idioma e
 * substituição do ficheiro. Eliminar fica bloqueado quando está em uso.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { formatDateTime } from "../../lib/format";
import {
  Button,
  ConfirmDestructive,
  EmptyState,
  Field,
  Input,
  InlineError,
  Modal,
  PageHeader,
  SearchInput,
  TableSkeleton,
} from "../../design/ui";
import { cmsMedia, i18nGet, i18nSet, rows, type CmsMedia, type Locale } from "./api";
import "./cms.css";

export default function CmsMediaPage() {
  const { token } = useAuth();
  const [assets, setAssets] = useState<CmsMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [over, setOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [detail, setDetail] = useState<CmsMedia | null>(null);
  const [confirm, setConfirm] = useState<CmsMedia | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const replaceRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    cmsMedia
      .list(token, { q: search || undefined })
      .then((data) => setAssets(rows<CmsMedia>(data)))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, search]);

  useEffect(load, [load]);

  const upload = async (files: FileList | File[]) => {
    if (!token) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append("file", file);
        form.append("filename", file.name);
        await cmsMedia.upload(token, form);
      }
      showToast("success", "Ficheiros carregados.");
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const openDetail = async (asset: CmsMedia) => {
    if (!token) return;
    try {
      // O detalhe traz a lista de onde o ficheiro está em uso.
      setDetail(await cmsMedia.get(token, asset.id));
    } catch {
      setDetail(asset);
    }
  };

  const saveAlt = async () => {
    if (!token || !detail) return;
    try {
      await cmsMedia.update(token, detail.id, { alt: detail.alt, folder: detail.folder });
      showToast("success", "Ficheiro actualizado.");
      setDetail(null);
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const replaceFile = async (file: File) => {
    if (!token || !detail) return;
    try {
      const form = new FormData();
      form.append("file", file);
      const updated: CmsMedia = await cmsMedia.replace(token, detail.id, form);
      setDetail(updated);
      showToast("success", "Ficheiro substituído em todas as páginas que o usam.");
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    }
  };

  const remove = async () => {
    if (!token || !confirm) return;
    try {
      await cmsMedia.remove(token, confirm.id);
      showToast("neutral", "Ficheiro eliminado.");
      setConfirm(null);
      load();
    } catch (e) {
      setBlocked((e as Error).message);
      setConfirm(null);
    }
  };

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <>
            <input
              accept="image/png,image/jpeg,image/webp,image/svg+xml,application/pdf"
              hidden
              multiple
              onChange={(e) => {
                if (e.target.files?.length) void upload(e.target.files);
                e.target.value = "";
              }}
              ref={fileRef}
              type="file"
            />
            <Button icon={<Upload size={16} />} loading={uploading} onClick={() => fileRef.current?.click()}>
              Carregar
            </Button>
          </>
        }
        crumbs={["Conteúdo", "Media"]}
        description="PNG, JPG, WEBP, SVG e PDF até 10 MB. Um ficheiro em uso não pode ser eliminado."
        title="Biblioteca de media"
      />

      <div className="bz-toolbar">
        <SearchInput onChange={setSearch} placeholder="Procurar por nome" value={search} />
      </div>

      <div
        className={`bzc-dropzone${over ? " bzc-dropzone-over" : ""}`}
        onDragLeave={() => setOver(false)}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (e.dataTransfer.files?.length) void upload(e.dataTransfer.files);
        }}
      >
        Arraste ficheiros para aqui, ou use o botão Carregar.
      </div>

      {blocked ? <InlineError>{blocked}</InlineError> : null}
      {error ? <InlineError>{error}</InlineError> : null}

      {loading ? (
        <TableSkeleton cols={4} rows={3} />
      ) : assets.length === 0 ? (
        <EmptyState
          action={<Button onClick={() => fileRef.current?.click()}>Carregar ficheiro</Button>}
          text="Os logótipos, imagens de partilha e documentos do site vivem aqui."
          title="Biblioteca vazia"
        />
      ) : (
        <div className="bzc-media">
          {assets.map((asset) => (
            <button className="bzc-mediacard" key={asset.id} onClick={() => openDetail(asset)} type="button">
              <span className="bzc-mediathumb">
                {asset.mime.startsWith("image/") ? <img alt="" src={asset.url} /> : <span className="bz-label">{asset.mime}</span>}
              </span>
              <span className="bzc-mediameta">
                <strong>{asset.filename}</strong>
                <small>
                  {asset.width && asset.height ? `${asset.width}×${asset.height} · ` : ""}
                  {Math.round(asset.bytes / 1024)} KB
                </small>
              </span>
            </button>
          ))}
        </div>
      )}

      <Modal
        footer={
          <>
            <Button
              className="bz-modal-foot-left"
              icon={<Trash2 size={15} />}
              onClick={() => {
                if (detail) setConfirm(detail);
              }}
              variant="danger"
            >
              Eliminar
            </Button>
            <Button onClick={() => setDetail(null)} variant="ghost">
              Fechar
            </Button>
            <Button onClick={saveAlt}>Guardar alterações</Button>
          </>
        }
        onClose={() => setDetail(null)}
        open={Boolean(detail)}
        title={detail?.filename || "Ficheiro"}
      >
        {detail ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="bzc-mediathumb" style={{ height: 200, borderRadius: 14, border: "1px solid var(--border)" }}>
              {detail.mime.startsWith("image/") ? <img alt="" src={detail.url} /> : <span className="bz-label">{detail.mime}</span>}
            </div>

            <div className="bz-formgrid">
              {(["pt", "en"] as Locale[]).map((locale) => (
                <Field key={locale} label={`Texto alternativo · ${locale.toUpperCase()}`}>
                  <Input
                    onChange={(e) => setDetail({ ...detail, alt: i18nSet(detail.alt, locale, e.target.value) })}
                    value={i18nGet(detail.alt, locale)}
                  />
                </Field>
              ))}
              <Field label="Pasta">
                <Input onChange={(e) => setDetail({ ...detail, folder: e.target.value })} value={detail.folder} />
              </Field>
              <Field label="Carregado">
                <Input disabled readOnly value={formatDateTime(detail.created_at)} />
              </Field>
            </div>

            <div>
              <span className="bz-field-label">Usado em</span>
              {detail.used_in && detail.used_in.length ? (
                <ul style={{ margin: "8px 0 0", paddingLeft: 18, font: "500 13px/1.7 var(--font-ui)" }}>
                  {detail.used_in.map((usage) => (
                    <li key={usage.id}>{usage.slug ? `/${usage.slug}` : "/"}</li>
                  ))}
                </ul>
              ) : (
                <p className="bz-field-hint" style={{ marginTop: 8 }}>
                  Não está a ser usado em nenhuma página.
                </p>
              )}
            </div>

            <div>
              <input
                accept="image/png,image/jpeg,image/webp,image/svg+xml,application/pdf"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void replaceFile(file);
                  e.target.value = "";
                }}
                ref={replaceRef}
                type="file"
              />
              <Button onClick={() => replaceRef.current?.click()} size="sm" variant="ghost">
                Substituir ficheiro
              </Button>
              <span className="bz-field-hint" style={{ display: "block", marginTop: 6 }}>
                A substituição troca a imagem em todas as páginas que a usam.
              </span>
            </div>
          </div>
        ) : null}
      </Modal>

      <ConfirmDestructive
        confirmLabel="Eliminar"
        message="O ficheiro é eliminado. Se estiver em uso, a operação é recusada e mostramos onde."
        onCancel={() => setConfirm(null)}
        onConfirm={remove}
        open={Boolean(confirm)}
        title="Eliminar ficheiro"
      />
    </div>
  );
}
