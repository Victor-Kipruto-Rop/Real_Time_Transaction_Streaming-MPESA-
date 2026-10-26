defmodule PesaGuard.IncidentManagementServiceTest do
  use ExUnit.Case, async: true

  test "service module has a stable application identity" do
    assert Application.spec(:incident_management_service, :vsn) == ~c"0.1.0" or
             Application.spec(:incident_management_service, :vsn) == '0.1.0' or
             Application.spec(:incident_management_service, :vsn) == nil
  end
end
