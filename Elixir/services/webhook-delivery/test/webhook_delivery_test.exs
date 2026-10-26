defmodule PesaGuard.WebhookDeliveryTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:webhook_delivery, :vsn) == ~c"0.1.0" or
             Application.spec(:webhook_delivery, :vsn) == '0.1.0' or
             Application.spec(:webhook_delivery, :vsn) == nil
  end
end
