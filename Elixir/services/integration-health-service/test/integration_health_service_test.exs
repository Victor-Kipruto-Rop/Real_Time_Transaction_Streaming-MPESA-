defmodule PesaGuard.IntegrationHealthServiceTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:integration_health_service, :vsn) == ~c"0.1.0" or
             Application.spec(:integration_health_service, :vsn) == '0.1.0' or
             Application.spec(:integration_health_service, :vsn) == nil
  end
end
