defmodule PesaGuard.NotificationService.Domain.DispatchPolicyTest do
  use ExUnit.Case, async: true

  alias PesaGuard.NotificationService.Domain.DispatchPolicy

  @intent %{"channel" => "email", "recipient_ref" => "recipient-reference-only"}
  @allowed %{
    consent: %{granted: true, purpose: "account_activity"},
    channel_enabled: true,
    suppressed: false
  }

  test "authorizes only when consent, channel preference, and suppression checks pass" do
    assert :ok = DispatchPolicy.authorize(@intent, @allowed)
  end

  test "fails closed when the trusted consent record is unavailable" do
    assert {:error, :consent_record_unavailable} =
             DispatchPolicy.authorize(@intent, %{channel_enabled: true, suppressed: false})
  end

  test "rejects revoked or absent consent" do
    context = put_in(@allowed, [:consent, :granted], false)
    assert {:error, :consent_not_granted} = DispatchPolicy.authorize(@intent, context)
  end

  test "requires an explicit consent purpose" do
    context = put_in(@allowed, [:consent, :purpose], "")
    assert {:error, :consent_purpose_missing} = DispatchPolicy.authorize(@intent, context)
  end

  test "honors a disabled channel preference" do
    assert {:error, :channel_preference_disabled} =
             DispatchPolicy.authorize(@intent, %{ @allowed | channel_enabled: false })
  end

  test "suppresses recipients on the suppression list" do
    assert {:error, :recipient_suppressed} =
             DispatchPolicy.authorize(@intent, %{ @allowed | suppressed: true })
  end

  test "fails closed for malformed policy context" do
    assert {:error, :invalid_policy_context} = DispatchPolicy.authorize(@intent, nil)
    assert {:error, :invalid_policy_context} = DispatchPolicy.authorize(%{}, @allowed)
  end
end
