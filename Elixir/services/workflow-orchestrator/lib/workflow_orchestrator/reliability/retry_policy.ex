defmodule PesaGuard.WorkflowOrchestrator.Reliability.RetryPolicy do
  @moduledoc "Bounded retry classification. Persist attempt counts and due times durably."

  @max_attempts 8
  @base_delay_ms 1_000
  @max_delay_ms 300_000

  @type failure_class :: :transient | :rate_limited | :permanent | :security

  def classify({:http_status, status}, _) when status in [408, 425, 429], do: :rate_limited
  def classify({:http_status, status}, _) when status >= 500 and status <= 599, do: :transient
  def classify({:timeout, _}, _), do: :transient
  def classify({:connection_error, _}, _), do: :transient
  def classify(:signature_invalid, _), do: :security
  def classify({:http_status, status}, _) when status >= 400 and status <= 499, do: :permanent
  def classify(_, _), do: :permanent

  @spec next_delay(non_neg_integer()) :: {:retry, non_neg_integer()} | :dead_letter
  def next_delay(attempt)
      when is_integer(attempt) and attempt >= 0 and attempt < @max_attempts do
    {:retry, min(@base_delay_ms * Integer.pow(2, min(attempt, 16)), @max_delay_ms)}
  end

  def next_delay(_), do: :dead_letter
end
