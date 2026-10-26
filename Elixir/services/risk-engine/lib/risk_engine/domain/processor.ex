defmodule PesaGuard.RiskEngine.Domain.Processor do
  @moduledoc "Computes deterministic risk assessments from normalized signals; no payment actions."

  def prepare(%{"signals" => signals, "model_or_rule_version" => version} = command)
      when is_map(signals) and is_binary(version) and map_size(signals) > 0 do
    values = Map.values(signals)

    if Enum.all?(values, &(is_number(&1) and &1 >= 0 and &1 <= 1)) do
      score = Enum.sum(values) / length(values)
      band = cond do
        score >= 0.7 -> "high"
        score >= 0.35 -> "medium"
        true -> "low"
      end

      explanation = signals |> Map.keys() |> Enum.map(&to_string/1) |> Enum.sort()
      {:ok, Map.merge(command, %{"risk_score" => Float.round(score, 4), "risk_band" => band, "signal_names" => explanation})}
    else
      {:error, :signals_must_be_between_zero_and_one}
    end
  end

  def prepare(_), do: {:error, :signals_and_model_version_required}
end
