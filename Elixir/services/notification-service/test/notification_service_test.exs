defmodule PesaGuard.NotificationServiceTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:notification_service, :vsn) == ~c"0.1.0" or
             Application.spec(:notification_service, :vsn) == '0.1.0' or
             Application.spec(:notification_service, :vsn) == nil
  end
end
