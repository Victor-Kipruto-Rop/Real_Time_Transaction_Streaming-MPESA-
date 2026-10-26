defmodule PesaGuard.WebhookDelivery.TargetPolicy do
  @moduledoc """
  Resolves and validates an outbound HTTPS target immediately before dispatch.

  Every DNS answer must be globally routable. The returned address is the exact
  IP that the transport must connect to; the transport must preserve the URL
  hostname for TLS SNI, certificate hostname verification, and the HTTP Host
  header. This closes the application-level DNS-rebinding gap between preflight
  validation and the TCP connection. Network egress controls remain required as
  defense in depth.
  """

  alias PesaGuard.WebhookDelivery.Domain.Processor

  def validate(url) when is_binary(url) do
    case resolve_target(url) do
      {:ok, _target} -> :ok
      {:error, reason} -> {:error, reason}
    end
  end

  def validate(_), do: {:error, :target_url_required}

  def resolve_target(url), do: resolve_target(url, &resolve/1)

  @doc false
  def resolve_target(url, resolver) when is_binary(url) and is_function(resolver, 1) do
    with {:ok, _} <- Processor.prepare(%{"target_url" => url, "payload" => %{}}),
         %URI{scheme: "https", host: host} = uri when is_binary(host) <- URI.parse(url),
         normalized_host <- String.trim(host, "[]"),
         false <- ip_literal?(normalized_host),
         {:ok, addresses} <- resolver.(normalized_host),
         true <- addresses != [] and Enum.all?(addresses, &public_address?/1),
         request_target <- request_target(uri),
         true <- is_binary(request_target) and not String.contains?(request_target, ["\r", "\n"]) do
      {:ok,
       %{
         host: normalized_host,
         port: uri.port || 443,
         address: hd(addresses),
         request_target: request_target
       }}
    else
      true -> {:error, :target_url_ip_literal_forbidden}
      false -> {:error, :target_url_private_host_forbidden}
      {:error, reason} -> {:error, reason}
      _ -> {:error, :target_url_dns_resolution_failed}
    end
  rescue
    _ -> {:error, :target_url_dns_resolution_failed}
  end

  def resolve_target(_, _), do: {:error, :target_url_required}

  defp request_target(%URI{path: path, query: query}) do
    base = if is_binary(path) and path != "", do: path, else: "/"
    if is_binary(query) and query != "", do: base <> "?" <> query, else: base
  end

  defp ip_literal?(host) do
    case :inet.parse_address(String.to_charlist(host)) do
      {:ok, _address} -> true
      {:error, _} ->
        case :inet.parse_ipv6_address(String.to_charlist(host)) do
          {:ok, _address} -> true
          {:error, _} -> false
        end
    end
  end

  defp resolve(host) do
    v4 =
      case :inet.getaddrs(String.to_charlist(host), :inet) do
        {:ok, addresses} -> addresses
        {:error, _} -> []
      end

    v6 =
      case :inet.getaddrs(String.to_charlist(host), :inet6) do
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

  defp public_address?({a, b, c, _d, _e, _f, _g, _h}) do
    # Global unicast IPv6 only; exclude special-use, documentation and transition
    # ranges that can tunnel or encode non-public IPv4 destinations.
    global_unicast? = a >= 0x2000 and a <= 0x3FFF
    teredo? = a == 0x2001 and b == 0x0000
    orchid_v1? = a == 0x2001 and b == 0x0010
    documentation? = (a == 0x2001 and b == 0x0DB8) or (a == 0x3FFF)
    six_to_four? = a == 0x2002
    _ = c
    global_unicast? and not (teredo? or orchid_v1? or documentation? or six_to_four?)
  end

  defp public_address?(_), do: false
end
