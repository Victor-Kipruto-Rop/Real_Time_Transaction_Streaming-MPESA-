defmodule PesaGuard.WebhookDelivery.TargetPolicy do
  @moduledoc """
  Applies defense-in-depth checks before customer webhook dispatch.

  Network egress controls must also block private/link-local destinations. DNS
  preflight alone cannot eliminate DNS-rebinding races between validation and
  connection establishment.
  """

  alias PesaGuard.WebhookDelivery.Domain.Processor

  def validate(url) when is_binary(url) do
    with {:ok, _} <- Processor.prepare(%{"target_url" => url, "payload" => %{}}),
         %URI{host: host} <- URI.parse(url),
         {:ok, addresses} <- resolve(host),
         true <- addresses != [] and Enum.all?(addresses, &public_address?/1) do
      :ok
    else
      false -> {:error, :target_url_private_host_forbidden}
      {:error, reason} -> {:error, reason}
      _ -> {:error, :target_url_dns_resolution_failed}
    end
  rescue
    _ -> {:error, :target_url_dns_resolution_failed}
  end

  def validate(_), do: {:error, :target_url_required}

  defp resolve(host) do
    v4 = case :inet.getaddrs(String.to_charlist(host), :inet) do
      {:ok, addresses} -> addresses
      {:error, _} -> []
    end

    v6 = case :inet.getaddrs(String.to_charlist(host), :inet6) do
      {:ok, addresses} -> addresses
      {:error, _} -> []
    end

    if v4 == [] and v6 == [], do: {:error, :target_url_dns_resolution_failed}, else: {:ok, v4 ++ v6}
  end

  defp public_address?({a, b, c, d}) do
    cond do
      a == 0 or a == 10 or a == 127 -> false
      a == 169 and b == 254 -> false
      a == 172 and b in 16..31 -> false
      a == 192 and b == 168 -> false
      a == 100 and b in 64..127 -> false
      a == 192 and b == 0 and c == 0 -> false
      a == 192 and b == 0 and c == 2 -> false
      a == 192 and b == 88 and c == 99 -> false
      a == 198 and b == 51 and c == 100 -> false
      a == 203 and b == 0 and c == 113 -> false
      a == 198 and b in 18..19 -> false
      a >= 224 -> false
      {a, b, c, d} == {255, 255, 255, 255} -> false
      true -> true
    end
  end

  defp public_address?({a, _b, _c, _d, _e, _f, _g, _h}) do
    # Global unicast IPv6 currently occupies 2000::/3. Reject ULA, link-local,
    # loopback, unspecified, multicast, and IPv4-mapped addresses by default.
    a >= 0x2000 and a <= 0x3FFF and not (a == 0x2001 and b == 0x0DB8)
  end

  defp public_address?(_), do: false
end
