import { t } from "../lib/i18n";
import { useUi } from "../ui/UiPreferences";
import { PageFrame, SectionCard } from "../ui/common";

export default function AuditPage({ embedded }: { embedded?: boolean }) {
  const { locale: lc } = useUi();

  return (
    <PageFrame kicker={t(lc, "security")} title={t(lc, "audit")}>
      <SectionCard title={t(lc, "audit")}>
        <div className="admin-empty-state">{t(lc, "auditDjangoAdmin")}</div>
      </SectionCard>
    </PageFrame>
  );
}
