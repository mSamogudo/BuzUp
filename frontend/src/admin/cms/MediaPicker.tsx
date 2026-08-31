/**
 * Escolha de um ficheiro da biblioteca, a partir de um campo de bloco ou do
 * SEO. Carrega ficheiros novos sem sair do sítio.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { Button, EmptyState, Modal, SearchInput, TableSkeleton } from "../../design/ui";
import { cmsMedia, rows, type CmsMedia } from "./api";

export function MediaPicker({
  open,
  onClose,
  onPick,
}: {
  open: boolean;
  onClose: () => void;
  onPick: (asset: CmsMedia) => void;
}) {
  const { token } = useAuth();
  const [assets, setAssets] = useState<CmsMedia[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    if (!token || !open) return;
    setLoading(true);
    cmsMedia
      .list(token, { q: search || undefined })
      .then((data) => setAssets(rows<CmsMedia>(data)))
      .catch((e: Error) => showToast("danger", e.message))
      .finally(() => setLoading(false));
  }, [token, open, search]);

  useEffect(load, [load]);

  const upload = async (file: File) => {
    if (!token) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("filename", file.name);
      const asset: CmsMedia = await cmsMedia.upload(token, form);
      showToast("success", "Ficheiro carregado.");
      onPick(asset);
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Modal
      footer={
        <>
          <input
            accept="image/png,image/jpeg,image/webp,image/svg+xml,application/pdf"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void upload(file);
              e.target.value = "";
            }}
            ref={fileRef}
            type="file"
          />
          <Button
            className="bz-modal-foot-left"
            icon={<Upload size={15} />}
            loading={uploading}
            onClick={() => fileRef.current?.click()}
            variant="ghost"
          >
            Carregar ficheiro
          </Button>
          <Button onClick={onClose} variant="ghost">
            Fechar
          </Button>
        </>
      }
      onClose={onClose}
      open={open}
      size="lg"
      title="Biblioteca de media"
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <SearchInput onChange={setSearch} placeholder="Procurar por nome" value={search} />
        {loading ? (
          <TableSkeleton cols={3} rows={3} />
        ) : assets.length === 0 ? (
          <EmptyState text="Carregue o primeiro ficheiro para o usar nas páginas." title="Biblioteca vazia" />
        ) : (
          <div className="bzc-media">
            {assets.map((asset) => (
              <button className="bzc-mediacard" key={asset.id} onClick={() => onPick(asset)} type="button">
                <span className="bzc-mediathumb">
                  {asset.mime.startsWith("image/") ? (
                    <img alt="" src={asset.url} />
                  ) : (
                    <span className="bz-label">{asset.mime}</span>
                  )}
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
      </div>
    </Modal>
  );
}
