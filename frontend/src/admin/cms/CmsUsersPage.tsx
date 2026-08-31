/**
 * CMS 3.11 — Utilizadores do CMS.
 *
 * Quem tem acesso ao conteúdo, com que papel e quando entrou pela última vez.
 * Matriz de capacidades por papel, só de leitura para papéis de sistema.
 *
 * Nota sobre o convite: a API não tem convite por email; o que existe é criar
 * a conta com uma senha temporária. É o que este ecrã faz — a senha aparece
 * uma vez, para ser entregue à pessoa, e ela muda-a no primeiro acesso.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { UserPlus } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { showToast } from "../../lib/toast";
import { formatDateTime } from "../../lib/format";
import { apiFetch, apiPost } from "../../lib/api";
import {
  Button,
  Card,
  DataTable,
  Field,
  InlineError,
  Input,
  Modal,
  PageHeader,
  Pill,
  Select,
  Tabs,
  type Column,
} from "../../design/ui";
import { rows } from "./api";

const CONTENT_CAPS = [
  "content.read",
  "content.write",
  "content.publish",
  "media.manage",
  "menus.manage",
  "seo.manage",
  "plans.manage",
  "requests.read",
];

interface Role {
  id: number;
  name: string;
  code: string;
  permissions: string[];
  is_system: boolean;
}

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  last_login: string | null;
  roles: { role_name?: string; role_code?: string; name?: string; code?: string }[];
}

function roleCodes(user: User): string[] {
  return (user.roles || []).map((r) => r.role_code || r.code || "").filter(Boolean);
}

function roleNames(user: User): string {
  const names = (user.roles || []).map((r) => r.role_name || r.name || "").filter(Boolean);
  return names.length ? names.join(", ") : "—";
}

export default function CmsUsersPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<"users" | "caps">("users");
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviting, setInviting] = useState(false);
  const [draft, setDraft] = useState({ username: "", email: "", first_name: "", last_name: "", role: "" });
  const [saving, setSaving] = useState(false);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    setError(null);
    Promise.all([apiFetch("/api/admin/users/", token), apiFetch("/api/admin/roles/", token)])
      .then(([userData, roleData]) => {
        setUsers(rows<User>(userData));
        setRoles(rows<Role>(roleData));
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  /** Só interessam as contas com alguma capacidade de conteúdo. */
  const contentRoleCodes = useMemo(
    () => new Set(roles.filter((r) => (r.permissions || []).some((p) => CONTENT_CAPS.includes(p) || p === "*")).map((r) => r.code)),
    [roles],
  );

  const contentUsers = useMemo(
    () => users.filter((user) => roleCodes(user).some((code) => contentRoleCodes.has(code))),
    [users, contentRoleCodes],
  );

  const invite = async () => {
    if (!token) return;
    setSaving(true);
    try {
      // Senha temporária forte, mostrada uma só vez.
      const password = `Bz-${Math.random().toString(36).slice(2, 8)}-${Math.random().toString(36).slice(2, 6)}`;
      const role = roles.find((r) => r.code === draft.role);
      await apiPost("/api/admin/users/", token, {
        username: draft.username,
        email: draft.email,
        first_name: draft.first_name,
        last_name: draft.last_name,
        password,
        role_ids: role ? [role.id] : [],
      });
      setTempPassword(password);
      setInviting(false);
      setDraft({ username: "", email: "", first_name: "", last_name: "", role: "" });
      load();
    } catch (e) {
      showToast("danger", (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const columns: Column<User>[] = [
    {
      key: "user",
      header: "Utilizador",
      render: (row) => (
        <span className="bz-cell-primary">
          <span className="bz-cell-id">{row.username}</span>
          <span className="bz-cell-name">{`${row.first_name} ${row.last_name}`.trim() || row.username}</span>
        </span>
      ),
    },
    { key: "email", header: "Email", render: (row) => <span>{row.email || "—"}</span> },
    { key: "role", header: "Papel", render: (row) => <Pill tone="info">{roleNames(row)}</Pill> },
    {
      key: "last",
      header: "Último acesso",
      render: (row) => <span className="bz-table-mono">{row.last_login ? formatDateTime(row.last_login) : "nunca"}</span>,
    },
    {
      key: "state",
      header: "Estado",
      render: (row) => <Pill tone={row.is_active ? "ok" : "mute"}>{row.is_active ? "Activo" : "Inactivo"}</Pill>,
    },
  ];

  return (
    <div className="bz-page">
      <PageHeader
        actions={
          <Button icon={<UserPlus size={16} />} onClick={() => setInviting(true)}>
            Convidar
          </Button>
        }
        crumbs={["Conteúdo", "Utilizadores do CMS"]}
        description="Quem pode editar o site, com que papel e quando entrou pela última vez."
        title="Utilizadores do CMS"
      />

      {error ? <InlineError>{error}</InlineError> : null}

      <Tabs
        onChange={setTab}
        options={[
          ["users", "Utilizadores"],
          ["caps", "Capacidades por papel"],
        ]}
        value={tab}
      />

      {tab === "users" ? (
        <DataTable
          columns={columns}
          empty={{
            title: "Ninguém com acesso ao conteúdo",
            text: "Convide alguém ou atribua o papel de Gestor de Conteúdo em Utilizadores do sistema.",
          }}
          error={error}
          loading={loading}
          onRetry={load}
          rowKey={(row) => String(row.id)}
          rows={contentUsers}
        />
      ) : (
        <Card flush large>
          <div className="bz-tablescroll">
            <table className="bz-table">
              <thead>
                <tr>
                  <th>Capacidade</th>
                  {roles
                    .filter((r) => contentRoleCodes.has(r.code))
                    .map((role) => (
                      <th key={role.id}>
                        {role.name}
                        {role.is_system ? " (sistema)" : ""}
                      </th>
                    ))}
                </tr>
              </thead>
              <tbody>
                {CONTENT_CAPS.map((cap) => (
                  <tr key={cap}>
                    <td className="bz-table-mono">{cap}</td>
                    {roles
                      .filter((r) => contentRoleCodes.has(r.code))
                      .map((role) => {
                        const has = (role.permissions || []).includes("*") || (role.permissions || []).includes(cap);
                        return (
                          <td key={role.id}>
                            <Pill tone={has ? "ok" : "mute"}>{has ? "Sim" : "Não"}</Pill>
                          </td>
                        );
                      })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="bz-tablefoot">
            <span>Só de leitura: os papéis de sistema editam-se em Utilizadores.</span>
          </div>
        </Card>
      )}

      <Modal
        footer={
          <>
            <Button onClick={() => setInviting(false)} variant="ghost">
              Cancelar
            </Button>
            <Button disabled={!draft.username} loading={saving} onClick={invite}>
              Criar acesso
            </Button>
          </>
        }
        onClose={() => setInviting(false)}
        open={inviting}
        title="Convidar para o CMS"
      >
        <div className="bz-formgrid">
          <Field label="Utilizador" required>
            <Input mono onChange={(e) => setDraft({ ...draft, username: e.target.value })} value={draft.username} />
          </Field>
          <Field label="Email">
            <Input onChange={(e) => setDraft({ ...draft, email: e.target.value })} type="email" value={draft.email} />
          </Field>
          <Field label="Nome">
            <Input onChange={(e) => setDraft({ ...draft, first_name: e.target.value })} value={draft.first_name} />
          </Field>
          <Field label="Apelido">
            <Input onChange={(e) => setDraft({ ...draft, last_name: e.target.value })} value={draft.last_name} />
          </Field>
          <Field hint="O papel define o que a pessoa pode fazer no CMS." label="Papel" span2>
            <Select onChange={(e) => setDraft({ ...draft, role: e.target.value })} value={draft.role}>
              <option value="">Sem papel</option>
              {roles.map((role) => (
                <option key={role.id} value={role.code}>
                  {role.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Modal>

      <Modal
        footer={
          <Button onClick={() => setTempPassword(null)}>Já anotei</Button>
        }
        onClose={() => setTempPassword(null)}
        open={Boolean(tempPassword)}
        size="sm"
        title="Acesso criado"
      >
        <p style={{ margin: "0 0 14px", font: "400 14px/1.6 var(--font-ui)", color: "var(--muted)" }}>
          Entregue esta senha temporária à pessoa. Não voltamos a mostrá-la.
        </p>
        <Input mono readOnly value={tempPassword || ""} />
      </Modal>
    </div>
  );
}
