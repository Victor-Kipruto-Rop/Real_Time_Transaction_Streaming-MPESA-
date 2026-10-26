defmodule PesaGuard.IntegrationHealthService.Domain.Processor do
  @moduledoc "Validates provider health check requests."

  @check_types ~w(connectivity authentication latency callback_delivery credential_validity)

  def prepare(%{"check_type" => type} = command) when is_binary(type) do
    timeout = Map.get(command, "timeout_ms", 5_000)

    cond do
      type not in @check_types -> {:error, :unsupported_check_type}
      not is_integer(timeout) or timeout < 100 or timeout > 30_000 -> {:error, :invalid_timeout}
      true -> {:ok, Map.put(command, "timeout_ms", timeout)}
    end
  end

  def prepare(_), do: {:error, :check_type_required}
end
