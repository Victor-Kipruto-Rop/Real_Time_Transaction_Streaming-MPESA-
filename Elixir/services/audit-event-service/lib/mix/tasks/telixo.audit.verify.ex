defmodule Mix.Tasks.Telixo.Audit.Verify do
  use Mix.Task

  @shortdoc "Independently verifies TELIXO audit hash chains using a separate read-only database URL"

  @impl Mix.Task
  def run(_args) do
    Application.ensure_all_started(:postgrex)

    verify_url = System.get_env("AUDIT_VERIFY_DATABASE_URL")
    writer_url = System.get_env("DATABASE_URL")
    verifier_identity = System.get_env("AUDIT_VERIFIER_IDENTITY", "independent-audit-verifier")

    unless is_binary(verify_url) and verify_url != "" and is_binary(writer_url) and writer_url != "" do
      Mix.raise("AUDIT_VERIFY_DATABASE_URL and DATABASE_URL are required")
    end

    if database_user(verify_url) == database_user(writer_url) do
      Mix.raise("AUDIT_VERIFY_DATABASE_URL must use a distinct read-only database role")
    end

    {:ok, reader} = Postgrex.start_link(url: verify_url, pool_size: 1)
    {:ok, writer} = Postgrex.start_link(url: writer_url, pool_size: 1)

    try do
      tenants = Postgrex.query!(reader, "SELECT DISTINCT tenant_id FROM telixo_audit_events ORDER BY tenant_id", []).rows

      failures =
        Enum.reduce(tenants, [], fn [tenant_id], acc ->
          started_at = DateTime.utc_now()
          rows =
            Postgrex.query!(reader, """
            SELECT event_id, tenant_sequence, idempotency_key, event_payload::text, previous_hash, event_hash
            FROM telixo_audit_events
            WHERE tenant_id = $1
            ORDER BY tenant_sequence ASC
            """, [tenant_id]).rows

          result = verify_rows(rows, tenant_id, 1, nil, 0, nil)

          {status, count, last_sequence, last_hash, failure_id, failure_code} =
            case result do
              {:ok, count, sequence, hash} -> {"verified", count, sequence, hash, nil, nil}
              {:error, event_id, code, count, sequence, hash} -> {"failed", count, sequence, hash, event_id, code}
            end

          verification_id = Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)

          Postgrex.query!(writer, """
          INSERT INTO telixo_audit_integrity_verification_runs
            (verification_id, tenant_id, verifier_identity, status, verified_event_count,
             last_verified_sequence, last_verified_hash, failure_event_id, failure_code,
             started_at, completed_at)
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
          """, [verification_id, tenant_id, verifier_identity, status, count, last_sequence,
                 last_hash, failure_id, failure_code, started_at])

          if status == "failed", do: [{tenant_id, failure_id, failure_code} | acc], else: acc
        end)

      if failures != [] do
        Mix.raise("Audit integrity verification failed for #{length(failures)} tenant(s): #{inspect(Enum.reverse(failures))}")
      end

      Mix.shell().info("Audit integrity verification passed for #{length(tenants)} tenant(s).")
    after
      GenServer.stop(reader)
      GenServer.stop(writer)
    end
  end

  defp verify_rows([], _tenant_id, _expected_sequence, _previous_hash, count, last_hash),
    do: {:ok, count, count, last_hash}

  defp verify_rows([[event_id, sequence, idempotency_key, payload_text, previous_hash, stored_hash] | rest],
         tenant_id, expected_sequence, expected_previous_hash, count, _last_hash) do
    with {:ok, event} <- Jason.decode(payload_text),
         expected_hash <- calculate_hash(tenant_id, idempotency_key, sequence, event, expected_previous_hash),
         true <- sequence == expected_sequence and previous_hash == expected_previous_hash and
                   is_binary(stored_hash) and Plug.Crypto.secure_compare(stored_hash, expected_hash) do
      verify_rows(rest, tenant_id, expected_sequence + 1, stored_hash, count + 1, stored_hash)
    else
      _ -> {:error, event_id, "hash_chain_mismatch", count, expected_sequence - 1, expected_previous_hash}
    end
  end

  defp calculate_hash(tenant_id, idempotency_key, sequence, event, previous_hash) do
    envelope = %{
      "tenant_id" => tenant_id,
      "idempotency_key" => idempotency_key,
      "tenant_sequence" => sequence,
      "event" => event,
      "previous_hash" => previous_hash
    }

    :crypto.hash(:sha256, canonical_json(envelope)) |> Base.encode16(case: :lower)
  end

  defp canonical_json(map) when is_map(map) do
    fields =
      map
      |> Enum.sort_by(fn {key, _value} -> key end)
      |> Enum.map(fn {key, value} -> Jason.encode!(key) <> ":" <> canonical_json(value) end)

    "{" <> Enum.join(fields, ",") <> "}"
  end

  defp canonical_json(list), do: "[" <> (list |> Enum.map(&canonical_json/1) |> Enum.join(",")) <> "]"
  defp canonical_json(value), do: Jason.encode!(value)

  defp database_user(url) do
    case URI.parse(url).userinfo do
      nil -> nil
      userinfo -> userinfo |> String.split(":", parts: 2) |> hd()
    end
  end
end
