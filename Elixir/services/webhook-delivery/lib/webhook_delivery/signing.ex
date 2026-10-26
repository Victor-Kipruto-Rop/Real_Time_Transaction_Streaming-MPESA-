defmodule PesaGuard.WebhookDelivery.Signing do
  @moduledoc """
  Builds and verifies versioned HMAC-SHA256 webhook signatures.

  The signed message is the exact UTF-8 timestamp, a dot, and the exact HTTP
  request body bytes. Receivers must verify the signature before parsing JSON,
  enforce the timestamp tolerance, and persist delivery IDs for replay
  deduplication. Timestamp validation alone is not durable replay prevention.
  """

  @default_tolerance_seconds 300
  @minimum_secret_bytes 32

  @type signature_error ::
          :invalid_secret
          | :invalid_timestamp
          | :invalid_signature
          | :timestamp_outside_tolerance

  @spec sign(binary(), integer() | binary(), binary()) :: {:ok, binary()} | {:error, signature_error()}
  def sign(secret, timestamp, body)
      when is_binary(secret) and is_binary(body) and
             (is_integer(timestamp) or is_binary(timestamp)) do
    with :ok <- validate_secret(secret),
         {:ok, timestamp_text} <- timestamp_text(timestamp) do
      digest = :crypto.mac(:hmac, :sha256, secret, timestamp_text <> "." <> body)
      {:ok, "v1=" <> Base.encode16(digest, case: :lower)}
    end
  end

  def sign(_, _, _), do: {:error, :invalid_signature}

  @spec headers(binary(), binary(), binary(), integer()) ::
          {:ok, [{binary(), binary()}]} | {:error, signature_error()}
  def headers(delivery_id, secret, body, timestamp \\ System.system_time(:second))

  def headers(delivery_id, secret, body, timestamp)
      when is_binary(delivery_id) and byte_size(delivery_id) > 0 and
             is_binary(body) and is_integer(timestamp) do
    with {:ok, signature} <- sign(secret, timestamp, body) do
      {:ok,
       [
         {"content-type", "application/json"},
         {"x-telixo-delivery-id", delivery_id},
         {"x-telixo-timestamp", Integer.to_string(timestamp)},
         {"x-telixo-signature", signature}
       ]}
    end
  end

  def headers(_, _, _, _), do: {:error, :invalid_signature}

  @spec verify(binary(), binary(), binary(), binary(), integer(), non_neg_integer()) ::
          :ok | {:error, signature_error()}
  def verify(secret, timestamp_header, signature_header, body, now \\ System.system_time(:second),
        tolerance \\ @default_tolerance_seconds)

  def verify(secret, timestamp_header, signature_header, body, now, tolerance)
      when is_binary(secret) and is_binary(timestamp_header) and
             is_binary(signature_header) and is_binary(body) and is_integer(now) and
             is_integer(tolerance) and tolerance >= 0 do
    with :ok <- validate_secret(secret),
         {timestamp, ""} <- Integer.parse(timestamp_header),
         true <- timestamp >= 0 do
      if abs(now - timestamp) > tolerance do
        {:error, :timestamp_outside_tolerance}
      else
        with {:ok, expected} <- sign(secret, timestamp, body) do
          if byte_size(expected) == byte_size(signature_header) and
               Plug.Crypto.secure_compare(expected, signature_header) do
            :ok
          else
            {:error, :invalid_signature}
          end
        end
      end
    else
      {:error, :invalid_secret} = error -> error
      :error -> {:error, :invalid_timestamp}
      {_timestamp, _rest} -> {:error, :invalid_timestamp}
      false -> {:error, :invalid_timestamp}
      {:error, _reason} -> {:error, :invalid_signature}
    end
  end

  def verify(_, _, _, _, _, _), do: {:error, :invalid_signature}

  defp validate_secret(secret) when byte_size(secret) >= @minimum_secret_bytes, do: :ok
  defp validate_secret(_), do: {:error, :invalid_secret}

  defp timestamp_text(timestamp) when is_integer(timestamp) and timestamp >= 0,
    do: {:ok, Integer.to_string(timestamp)}

  defp timestamp_text(timestamp) when is_binary(timestamp) do
    case Integer.parse(timestamp) do
      {value, ""} when value >= 0 -> {:ok, timestamp}
      _ -> {:error, :invalid_timestamp}
    end
  end

  defp timestamp_text(_), do: {:error, :invalid_timestamp}
end
