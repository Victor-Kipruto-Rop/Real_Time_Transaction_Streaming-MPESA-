defmodule PesaGuard.WebhookDelivery.SecretBox do
  @moduledoc """
  AES-256-GCM envelope encryption for customer webhook signing secrets.

  WEBHOOK_ENCRYPTION_KEY must be base64-encoded 32-byte key material supplied by
  a secret manager. The key is never persisted alongside ciphertext.
  """

  @nonce_bytes 12
  @tag_bytes 16

  def encrypt(secret) when is_binary(secret) and byte_size(secret) >= 32 do
    with {:ok, key} <- encryption_key() do
      nonce = :crypto.strong_rand_bytes(@nonce_bytes)
      {ciphertext, tag} = :crypto.crypto_one_time_aead(:aes_256_gcm, key, nonce, secret, "telixo-webhook-secret:v1", true)
      {:ok, "v1:" <> Base.url_encode64(nonce <> tag <> ciphertext, padding: false)}
    end
  rescue
    _ -> {:error, :encryption_failed}
  end

  def encrypt(_), do: {:error, :invalid_secret}

  def decrypt("v1:" <> encoded) do
    with {:ok, packed} <- Base.url_decode64(encoded, padding: false),
         true <- byte_size(packed) >= @nonce_bytes + @tag_bytes,
         <<nonce::binary-size(@nonce_bytes), tag::binary-size(@tag_bytes), ciphertext::binary>> <- packed,
         {:ok, key} <- encryption_key(),
         plaintext when is_binary(plaintext) <-
           :crypto.crypto_one_time_aead(:aes_256_gcm, key, nonce, ciphertext, "telixo-webhook-secret:v1", tag, false) do
      {:ok, plaintext}
    else
      _ -> {:error, :decryption_failed}
    end
  rescue
    _ -> {:error, :decryption_failed}
  end

  def decrypt(_), do: {:error, :decryption_failed}

  defp encryption_key do
    case System.get_env("WEBHOOK_ENCRYPTION_KEY") do
      nil -> {:error, :encryption_key_missing}
      encoded ->
        case Base.decode64(encoded) do
          {:ok, key} when byte_size(key) == 32 -> {:ok, key}
          _ -> {:error, :encryption_key_invalid}
        end
    end
  end
end
