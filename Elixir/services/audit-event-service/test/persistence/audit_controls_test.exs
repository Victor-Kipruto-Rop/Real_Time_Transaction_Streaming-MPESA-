if System.get_env("DATABASE_URL") do
  defmodule PesaGuard.AuditEventService.Persistence.AuditControlsTest do
    use ExUnit.Case, async: false

    alias PesaGuard.AuditEventService.Persistence.AuditControls

    test "persists tenant retention policy and append-only privileged access history" do
      tenant = "audit-controls-" <> Base.encode16(:crypto.strong_rand_bytes(8))
      actor = "compliance-operator"
      reason = "approved compliance retention review"
      request_id = "request-" <> Base.encode16(:crypto.strong_rand_bytes(8))

      assert {:ok, default_policy} = AuditControls.get_retention_policy(tenant)
      assert default_policy.configured == false
      assert default_policy.retention_days == 2555
      assert default_policy.legal_hold == false

      assert {:ok, policy} =
               AuditControls.set_retention_policy(tenant, 3650, true, actor, reason, request_id)

      assert policy.retention_days == 3650
      assert policy.legal_hold == true
      assert policy.updated_by == actor
      assert :ok = AuditControls.log_privileged_access(tenant, actor, "audit.export_requested", reason, request_id)

      assert {:ok, %{rows: [[2]]}} =
               Postgrex.query(
                 PesaGuard.AuditEventService.Persistence.PostgresConnection,
                 "SELECT count(*)::int FROM telixo_audit_privileged_access_log WHERE tenant_id = $1",
                 [tenant]
               )

      assert {:error, %Postgrex.Error{}} =
               Postgrex.query(
                 PesaGuard.AuditEventService.Persistence.PostgresConnection,
                 "UPDATE telixo_audit_privileged_access_log SET reason = 'tampered' WHERE tenant_id = $1",
                 [tenant]
               )
    end
  end
end
