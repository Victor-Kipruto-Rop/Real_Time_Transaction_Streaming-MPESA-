defmodule PesaGuard.WebhookDelivery.EndpointCircuitBreakerTest do
  use ExUnit.Case, async: false

  alias PesaGuard.WebhookDelivery.EndpointCircuitBreaker

  setup do
    start_supervised!({EndpointCircuitBreaker, threshold: 2, open_ms: 40, max_entries: 2})
    :ok
  end

  test "opens after the configured number of failures and permits one half-open probe" do
    url = "https://hooks.example.com/events"

    assert :ok = EndpointCircuitBreaker.allow?(url)
    EndpointCircuitBreaker.record_failure(url)
    assert :ok = EndpointCircuitBreaker.allow?(url)
    EndpointCircuitBreaker.record_failure(url)
    assert {:error, :circuit_open} = EndpointCircuitBreaker.allow?(url)

    Process.sleep(50)
    assert :ok = EndpointCircuitBreaker.allow?(url)
    assert {:error, :circuit_open} = EndpointCircuitBreaker.allow?(url)

    EndpointCircuitBreaker.record_success(url)
    assert :ok = EndpointCircuitBreaker.allow?(url)
  end

  test "keeps circuit state isolated by origin" do
    EndpointCircuitBreaker.record_failure("https://one.example.com/hook")
    EndpointCircuitBreaker.record_failure("https://one.example.com/another-path")

    assert {:error, :circuit_open} = EndpointCircuitBreaker.allow?("https://one.example.com/third-path")
    assert :ok = EndpointCircuitBreaker.allow?("https://two.example.com/hook")
  end

  test "rejects malformed endpoints without creating a circuit" do
    assert {:error, :invalid_endpoint} = EndpointCircuitBreaker.allow?("/relative/path")
  end
end
