defmodule PesaGuard.AuditEventService.AdminControllerTest do
  use ExUnit.Case, async: true

  alias PesaGuard.AuditEventService.AdminController

  test "denies retention access without a privileged JWT role" do
    conn =
      Plug.Test.conn(:get, "/v1/admin/retention-policy")
      |> Plug.Conn.assign(:tenant_context, %{
        tenant_id: "tenant-test",
        subject: "ordinary-user",
        claims: %{"roles" => ["tenant_user"]}
      })

    response = AdminController.get_retention_policy(conn, %{})

    assert response.status == 403
    assert response.resp_body =~ "privileged_role_required"
  end

  test "requires an audit reason even for a privileged role" do
    conn =
      Plug.Test.conn(:get, "/v1/admin/retention-policy")
      |> Plug.Conn.assign(:tenant_context, %{
        tenant_id: "tenant-test",
        subject: "compliance-user",
        claims: %{"roles" => ["audit_compliance"]}
      })

    response = AdminController.get_retention_policy(conn, %{})

    assert response.status == 400
    assert response.resp_body =~ "audit_reason_required"
  end
end
