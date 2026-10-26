defmodule TELIXO.WorkflowOrchestrator.Security.TenantContext do
  @moduledoc "Fail-closed tenant helpers. Claims must already be cryptographically verified."
  @spec from_verified_claims(map()) :: {:ok, %{tenant_id: binary(), subject: binary()}} | {:error, :unauthorized}
  def from_verified_claims(%{"tenant_id" => tenant, "sub" => subject}) when is_binary(tenant) and byte_size(tenant) > 0 and is_binary(subject) and byte_size(subject) > 0, do: {:ok, %{tenant_id: tenant, subject: subject}}
  def from_verified_claims(_), do: {:error, :unauthorized}
  @spec authorize_tenant(term(), term()) :: :ok | {:error, :forbidden}
  def authorize_tenant(tenant, resource_tenant) when is_binary(tenant) and is_binary(resource_tenant), do: if(tenant == resource_tenant, do: :ok, else: {:error, :forbidden})
  def authorize_tenant(_, _), do: {:error, :forbidden}
end