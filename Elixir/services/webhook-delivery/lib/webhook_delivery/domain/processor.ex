defmodule PesaGuard.WebhookDelivery.Domain.Processor do
  @moduledoc "Validates webhook targets before enqueueing delivery work."

  def prepare(%{"target_url" => target_url} = command) when is_binary(target_url) do
    uri = URI.parse(target_url)
    host = String.downcase(uri.host || "")

    cond do
      uri.scheme != "https" -> {:error, :target_url_must_use_https}
      host == "" -> {:error, :target_url_host_required}
      uri.userinfo != nil -> {:error, :target_url_credentials_forbidden}
      uri.port not in [nil, 443] -> {:error, :target_url_port_forbidden}
      host in ["localhost", "127.0.0.1", "::1"] -> {:error, :target_url_private_host_forbidden}
      String.ends_with?(host, ".local") or String.ends_with?(host, ".internal") ->
        {:error, :target_url_private_host_forbidden}
      ip_literal?(host) -> {:error, :target_url_ip_literal_forbidden}
      not is_map(Map.get(command, "payload")) -> {:error, :payload_must_be_object}
      true -> {:ok, command}
    end
  end

  def prepare(_), do: {:error, :target_url_required}

  defp ip_literal?(host) do
    normalized_host = host |> String.trim_leading("[") |> String.trim_trailing("]")

    case :inet.parse_address(String.to_charlist(normalized_host)) do
      {:ok, _address} -> true
      {:error, _reason} ->
        case :inet.parse_ipv6_address(String.to_charlist(normalized_host)) do
          {:ok, _address} -> true
          {:error, _reason} -> false
        end
    end
  end
end
