defmodule PesaGuard.WebhookDelivery.PinnedHttpClient do
  @moduledoc """
  Minimal HTTPS POST transport that connects to the IP selected by TargetPolicy.

  It deliberately does not perform a second DNS lookup. TLS SNI and certificate
  hostname verification still use the original URL hostname.
  """

  @connect_timeout_ms 2_000
  @request_timeout_ms 5_000
  @max_status_line_bytes 8_192

  def post(target, headers, body)
      when is_map(target) and is_list(headers) and is_binary(body) do
    with true <- valid_headers?(headers),
         {:ok, tcp_socket} <- connect_tcp(target.address, target.port) do
      request_over_tls(tcp_socket, target, headers, body)
    else
      false -> {:error, :invalid_request}
      {:error, reason} -> {:error, reason}
    end
  rescue
    _ -> {:error, :request_failed}
  catch
    :exit, _ -> {:error, :request_failed}
  end

  def post(_, _, _), do: {:error, :invalid_request}

  defp connect_tcp(address, port) do
    family = if tuple_size(address) == 8, do: [:inet6], else: []

    :gen_tcp.connect(
      address,
      port,
      [:binary, active: false, packet: :raw] ++ family,
      @connect_timeout_ms
    )
  end

  defp request_over_tls(tcp_socket, target, headers, body) do
    tls_options = [
      verify: :verify_peer,
      cacerts: :public_key.cacerts_get(),
      server_name_indication: String.to_charlist(target.host),
      customize_hostname_check: [
        match_fun: :public_key.pkix_verify_hostname_match_fun(:https)
      ],
      depth: 5,
      active: false
    ]

    case :ssl.connect(tcp_socket, tls_options, @request_timeout_ms) do
      {:ok, ssl_socket} ->
        try do
          with :ok <- :ssl.send(ssl_socket, build_request(target, headers, body)),
               {:ok, status} <- read_status_line(ssl_socket, <<>>, @request_timeout_ms) do
            {:ok, status}
          end
        after
          :ssl.close(ssl_socket)
        end

      {:error, _reason} ->
        safe_tcp_close(tcp_socket)
        {:error, :tls_connection_failed}
    end
  rescue
    _ ->
      safe_tcp_close(tcp_socket)
      {:error, :request_failed}
  catch
    :exit, _ ->
      safe_tcp_close(tcp_socket)
      {:error, :request_failed}
  end

  defp safe_tcp_close(socket) do
    try do
      :gen_tcp.close(socket)
    rescue
      _ -> :ok
    catch
      :exit, _ -> :ok
    end
  end

  defp build_request(target, headers, body) do
    host_header = if target.port == 443, do: target.host, else: "#{target.host}:#{target.port}"

    header_lines =
      Enum.map(headers, fn {name, value} ->
        "#{name}: #{value}\r\n"
      end)

    [
      "POST ", target.request_target, " HTTP/1.1\r\n",
      "Host: ", host_header, "\r\n",
      "Connection: close\r\n",
      "Content-Length: ", Integer.to_string(byte_size(body)), "\r\n",
      header_lines,
      "\r\n",
      body
    ]
    |> IO.iodata_to_binary()
  end

  @doc false
  def parse_status_line(status_line) when is_binary(status_line) do
    case Regex.run(~r/^HTTP\/\d(?:\.\d)?\s+(\d{3})(?:\s|$)/, status_line) do
      [_, status] -> {:ok, String.to_integer(status)}
      _ -> {:error, :invalid_http_response}
    end
  end

  def parse_status_line(_), do: {:error, :invalid_http_response}

  defp read_status_line(socket, buffer, timeout) do
    deadline = System.monotonic_time(:millisecond) + timeout
    read_status_line_until(socket, buffer, deadline)
  end

  defp read_status_line_until(socket, buffer, deadline)
       when byte_size(buffer) <= @max_status_line_bytes do
    case :binary.match(buffer, "\r\n") do
      {index, 2} ->
        status_line = binary_part(buffer, 0, index)

        case parse_status_line(status_line) do
          {:ok, status} -> {:ok, status}
          {:error, reason} -> {:error, reason}
        end

      :nomatch ->
        remaining = deadline - System.monotonic_time(:millisecond)

        if remaining <= 0 do
          {:error, :response_timeout}
        else
          case :ssl.recv(socket, 0, remaining) do
            {:ok, chunk} when byte_size(chunk) > 0 ->
              read_status_line_until(socket, buffer <> chunk, deadline)

            {:error, :closed} ->
              {:error, :empty_http_response}

            {:error, _} ->
              {:error, :response_read_failed}
          end
        end
    end
  end

  defp read_status_line_until(_socket, _buffer, _deadline), do: {:error, :http_status_line_too_large}

  defp valid_headers?(headers) do
    Enum.all?(headers, fn
      {name, value} when is_binary(name) and is_binary(value) ->
        not String.contains?(name, ["\r", "\n", ":"]) and
          not String.contains?(value, ["\r", "\n"])

      _ ->
        false
    end)
  end
end
