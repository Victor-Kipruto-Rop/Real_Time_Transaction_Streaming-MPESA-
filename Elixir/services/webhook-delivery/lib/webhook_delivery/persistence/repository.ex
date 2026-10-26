defmodule PesaGuard.WebhookDelivery.Persistence.Repository do
  @moduledoc "Tenant-scoped durable persistence contract."

  @callback get(binary(), binary()) :: {:ok, map()} | {:error, :not_found | :unavailable}
  @callback insert_once(binary(), binary(), map()) ::
              {:ok, map()} | {:error, :duplicate | :conflict | :unavailable}
  @callback transition(binary(), binary(), binary(), map()) ::
              {:ok, map()} | {:error, :conflict | :invalid_transition | :unavailable}
end
