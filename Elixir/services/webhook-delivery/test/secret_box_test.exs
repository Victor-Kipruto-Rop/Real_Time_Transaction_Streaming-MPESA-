defmodule PesaGuard.WebhookDelivery.SecretBoxTest do
  use ExUnit.Case, async: false
  alias PesaGuard.WebhookDelivery.SecretBox

  setup do
    previous = System.get_env("WEBHOOK_ENCRYPTION_KEY")
    System.put_env("WEBHOOK_ENCRYPTION_KEY", Base.encode64(:crypto.strong_rand_bytes(32)))
    on_exit(fn ->
      if previous, do: System.put_env("WEBHOOK_ENCRYPTION_KEY", previous),
        else: System.delete_env("WEBHOOK_ENCRYPTION_KEY")
    end)
    :ok
  end

  test "round-trips secrets without storing plaintext" do
    secret = String.duplicate("s", 40)
    assert {:ok, encrypted} = SecretBox.encrypt(secret)
    refute encrypted =~ secret
    assert {:ok, ^secret} = SecretBox.decrypt(encrypted)
  end

  test "rejects weak secrets and tampered ciphertext" do
    assert {:error, :invalid_secret} = SecretBox.encrypt("short")
    assert {:ok, encrypted} = SecretBox.encrypt(String.duplicate("s", 40))
    assert {:error, :decryption_failed} = SecretBox.decrypt(encrypted <> "tampered")
  end
end
