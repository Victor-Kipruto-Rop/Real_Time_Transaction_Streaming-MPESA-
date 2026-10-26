defmodule PesaGuard.FraudDetection.Domain.Processor do
  @moduledoc "Evaluates versioned fraud features into explainable signals; never moves funds."

  def prepare(%{"features" => features, "rule_version" => version} = command)
      when is_map(features) and is_binary(version) do
    amount_deviation = numeric_feature(features, "amount_deviation", 0.0, 1.0)
    velocity_count = numeric_feature(features, "velocity_count", 0.0, 100.0)
    new_device = Map.get(features, "new_device", false)

    if is_nil(amount_deviation) or is_nil(velocity_count) or not is_boolean(new_device) do
      {:error, :invalid_features}
    else
      score =
        min(
          1.0,
          amount_deviation * 0.55 + min(velocity_count / 100.0, 1.0) * 0.30 +
            if(new_device, do: 0.15, else: 0.0)
        )

      band = cond do
        score >= 0.75 -> "high"
        score >= 0.45 -> "review"
        true -> "low"
      end

      {:ok, Map.merge(command, %{"risk_score" => Float.round(score, 4), "risk_band" => band})}
    end
  end

  def prepare(_), do: {:error, :features_and_rule_version_required}

  defp numeric_feature(features, key, minimum, maximum) do
    case Map.get(features, key) do
      value when is_number(value) and value >= minimum and value <= maximum -> value
      _ -> nil
    end
  end
end
