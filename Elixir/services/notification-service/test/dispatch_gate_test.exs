defmodule PesaGuard.NotificationService.DispatchGateTest do
  use ExUnit.Case, async: true

  alias PesaGuard.NotificationService.DispatchGate

  test "does not invoke the provider when persisted policy denies dispatch" do
    parent = self()
    policy_check = fn _tenant, _intent -> {:error, :consent_not_granted} end
    sender = fn _intent -> send(parent, :provider_called); {:ok, :sent} end

    assert {:error, {:policy_denied, :consent_not_granted}} =
             DispatchGate.dispatch_with("tenant-a", intent(), policy_check, sender)

    refute_received :provider_called
  end

  test "runs the provider only after a successful current policy check" do
    parent = self()

    policy_check = fn "tenant-a", _intent ->
      send(parent, :policy_checked)
      :ok
    end

    sender = fn payload ->
      assert_received :policy_checked
      send(parent, {:provider_called, payload["purpose"]})
      {:ok, :accepted}
    end

    assert {:ok, :accepted} =
             DispatchGate.dispatch_with("tenant-a", intent(), policy_check, sender)

    assert_received {:provider_called, "account_activity"}
  end

  test "fails closed when policy storage raises or exits" do
    sender = fn _ -> flunk("provider must not be called when policy cannot be checked") end

    assert {:error, :dispatch_gate_unavailable} =
             DispatchGate.dispatch_with("tenant-a", intent(), fn _, _ -> raise "db unavailable" end, sender)

    assert {:error, :dispatch_gate_unavailable} =
             DispatchGate.dispatch_with("tenant-a", intent(), fn _, _ -> exit(:db_down) end, sender)
  end

  test "normalizes provider exceptions and rejects invalid provider results" do
    assert {:error, :provider_dispatch_failed} =
             DispatchGate.dispatch_with("tenant-a", intent(), fn _, _ -> :ok end, fn _ -> raise "provider error" end)

    assert {:error, :invalid_provider_result} =
             DispatchGate.dispatch_with("tenant-a", intent(), fn _, _ -> :ok end, fn _ -> :ok end)
  end

  test "rejects malformed dispatch requests" do
    assert {:error, :invalid_dispatch_request} = DispatchGate.dispatch("", %{}, fn _ -> {:ok, :sent} end)
    assert {:error, :invalid_dispatch_request} = DispatchGate.dispatch("tenant-a", %{}, :not_a_function)
  end

  defp intent do
    %{
      "recipient_ref" => "recipient-a",
      "channel" => "email",
      "purpose" => "account_activity"
    }
  end
end
