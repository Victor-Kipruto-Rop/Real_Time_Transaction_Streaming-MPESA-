defmodule PesaGuard.FraudDetection.Contracts.Event do
  @moduledoc "Versioned event-envelope validation for fraud-detection."

  @required ~w(event_id tenant_id event_type occurred_at schema_version payload)

  @spec validate(term()) :: {:ok, map()} | {:error, {:invalid_event, [binary()]}}
  def validate(event) when is_map(event) do
    missing = Enum.filter(@required, fn key -> blank?(Map.get(event, key)) end)

    invalid =
      []
      |> maybe_add(not is_binary(Map.get(event, "event_id")), "event_id")
      |> maybe_add(not is_binary(Map.get(event, "tenant_id")), "tenant_id")
      |> maybe_add(not is_binary(Map.get(event, "event_type")), "event_type")
      |> maybe_add(not is_map(Map.get(event, "payload")), "payload")
      |> maybe_add(
        not is_integer(Map.get(event, "schema_version")) or
          Map.get(event, "schema_version") < 1,
        "schema_version"
      )

    errors = Enum.uniq(missing ++ invalid)
    if errors == [], do: {:ok, event}, else: {:error, {:invalid_event, errors}}
  end

  def validate(_), do: {:error, {:invalid_event, ["event must be a map"]}}
  defp maybe_add(errors, true, field), do: [field | errors]
  defp maybe_add(errors, false, _field), do: errors
  defp blank?(nil), do: true
  defp blank?(value) when is_binary(value), do: String.trim(value) == ""
  defp blank?(_), do: false
end
