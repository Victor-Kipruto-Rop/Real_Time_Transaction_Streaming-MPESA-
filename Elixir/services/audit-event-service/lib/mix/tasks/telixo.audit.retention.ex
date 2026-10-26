defmodule Mix.Tasks.Telixo.Audit.Retention do
  use Mix.Task

  @shortdoc "Archives and purges expired audit-ledger prefixes under a dedicated database role"

  @impl Mix.Task
  def run(_args) do
    Application.ensure_all_started(:postgrex)

    database_url = System.get_env("AUDIT_RETENTION_DATABASE_URL")
    archive_directory = System.get_env("AUDIT_ARCHIVE_DIRECTORY")
    execute? = System.get_env("AUDIT_RETENTION_EXECUTE") == "true"
    actor_id = System.get_env("AUDIT_RETENTION_ACTOR", "scheduled-retention-job")
    reason = System.get_env("AUDIT_RETENTION_REASON", "")
    request_id = Base.url_encode64(:crypto.strong_rand_bytes(12), padding: false)

    unless is_binary(database_url) and database_url != "" do
      Mix.raise("AUDIT_RETENTION_DATABASE_URL is required")
    end

    unless database_user(database_url) == "telixo_audit_retention_executor" do
      Mix.raise("AUDIT_RETENTION_DATABASE_URL must use the dedicated telixo_audit_retention_executor role")
    end

    if execute? and (not is_binary(archive_directory) or archive_directory == "") do
      Mix.raise("AUDIT_ARCHIVE_DIRECTORY is required when AUDIT_RETENTION_EXECUTE=true")
    end

    if execute? and (byte_size(String.trim(reason)) < 10 or byte_size(reason) > 500) do
      Mix.raise("AUDIT_RETENTION_REASON must explain the approved purge (10-500 characters)")
    end

    {:ok, connection} = Postgrex.start_link(url: database_url, pool_size: 1)

    try do
      tenants =
        Postgrex.query!(
          connection,
          """
          SELECT tenant_id, COALESCE(retention_days, 2555), COALESCE(legal_hold, FALSE)
          FROM (
            SELECT DISTINCT tenant_id FROM telixo_audit_events
          ) events
          LEFT JOIN telixo_audit_retention_policies USING (tenant_id)
          ORDER BY tenant_id
          """,
          []
        ).rows

      Enum.each(tenants, fn [tenant_id, retention_days, legal_hold] ->
        cond do
          legal_hold ->
            Mix.shell().info("Skipping tenant #{tenant_id}: legal hold is active")

          true ->
            cutoff = DateTime.add(DateTime.utc_now(), -retention_days * 86_400, :second)
            expired = expired_prefix(connection, tenant_id, cutoff)

            case expired do
              [] ->
                :ok

              events ->
                if execute? do
                  archive_and_purge!(
                    connection,
                    archive_directory,
                    tenant_id,
                    events,
                    actor_id,
                    String.trim(reason),
                    request_id
                  )
                else
                  first_sequence = Enum.at(hd(events), 2)
                  last_sequence = Enum.at(List.last(events), 2)
                  Mix.shell().info("DRY RUN: tenant=#{tenant_id} events=#{length(events)} sequence=#{first_sequence}..#{last_sequence}")
                end
            end
        end
      end)

      unless execute? do
        Mix.shell().info("Dry run only. Set AUDIT_RETENTION_EXECUTE=true after verifying the immutable archive and legal-hold controls.")
      end
    after
      GenServer.stop(connection)
    end
  end

  defp expired_prefix(connection, tenant_id, cutoff) do
    {first_sequence, previous_hash} =
      case Postgrex.query!(
             connection,
             "SELECT first_retained_sequence, previous_hash FROM telixo_audit_chain_anchors WHERE tenant_id = $1",
             [tenant_id]
           ).rows do
        [[sequence, hash]] -> {sequence, hash}
        [] -> {1, nil}
      end

    rows =
      Postgrex.query!(
        connection,
        """
        SELECT event_id, tenant_id, tenant_sequence, idempotency_key, actor_type, action,
               occurred_at, event_payload::text, previous_hash, event_hash, recorded_at
        FROM telixo_audit_events
        WHERE tenant_id = $1 AND tenant_sequence >= $2
        ORDER BY tenant_sequence ASC
        """,
        [tenant_id, first_sequence]
      ).rows

    case verify_chain_rows(rows, tenant_id, first_sequence, previous_hash) do
      :ok ->
        Enum.take_while(rows, fn row -> DateTime.compare(Enum.at(row, 10), cutoff) == :lt end)

      {:error, event_id} ->
        Mix.raise("Refusing retention purge: hash-chain integrity failed at event #{event_id} for tenant #{tenant_id}")
    end
  end

  defp archive_and_purge!(connection, archive_directory, tenant_id, events, actor_id, reason, request_id) do
    first_sequence = Enum.at(hd(events), 2)
    last_event = List.last(events)
    last_sequence = Enum.at(last_event, 2)
    last_hash = Enum.at(last_event, 9)
    archive_id = random_id()
    archive_bytes = Enum.map_join(events, "\n", &encode_event/1) <> "\n"
    archive_hash = :crypto.hash(:sha256, archive_bytes) |> Base.encode16(case: :lower)
    safe_tenant = Base.url_encode64(tenant_id, padding: false)
    filename = "#{safe_tenant}-#{first_sequence}-#{last_sequence}-#{archive_id}.jsonl"
    archive_path = Path.join(archive_directory, filename)

    File.mkdir_p!(archive_directory)

    case File.open(archive_path, [:write, :binary, :exclusive], 0o600, fn file ->
           with :ok <- IO.binwrite(file, archive_bytes),
                :ok <- :file.sync(file) do
             :ok
           end
         end) do
      {:ok, :ok} -> :ok
      {:ok, {:error, reason}} -> Mix.raise("Could not durably write audit archive: #{inspect(reason)}")
      {:error, reason} -> Mix.raise("Could not create audit archive: #{inspect(reason)}")
    end

    archived_bytes = File.read!(archive_path)
    archived_hash = :crypto.hash(:sha256, archived_bytes) |> Base.encode16(case: :lower)

    unless Plug.Crypto.secure_compare(archive_hash, archived_hash) do
      Mix.raise("Audit archive verification failed; no ledger rows were purged")
    end

    result =
      Postgrex.transaction(connection, fn conn ->
        Postgrex.query!(conn, "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", [tenant_id])

        policy =
          Postgrex.query!(
            conn,
            "SELECT retention_days, legal_hold FROM telixo_audit_retention_policies WHERE tenant_id = $1 FOR UPDATE",
            [tenant_id]
          ).rows

        case policy do
          [[_days, true]] -> raise "Legal hold became active; refusing to purge tenant #{tenant_id}"
          _ -> :ok
        end

        [current_days] =
          case policy do
            [[days, false]] -> [days]
            [] -> [2555]
          end

        current_cutoff = DateTime.add(DateTime.utc_now(), -current_days * 86_400, :second)

        {:ok, %{rows: [[count, min_sequence, max_sequence]]}} =
          Postgrex.query(
            conn,
            """
            SELECT count(*)::int, min(tenant_sequence), max(tenant_sequence)
            FROM telixo_audit_events
            WHERE tenant_id = $1 AND tenant_sequence BETWEEN $2 AND $3 AND recorded_at < $4
            """,
            [tenant_id, first_sequence, last_sequence, current_cutoff]
          )

        unless count == length(events) and min_sequence == first_sequence and max_sequence == last_sequence do
          raise "Expired prefix changed during archive; refusing to purge tenant #{tenant_id}"
        end

        Postgrex.query!(conn, "SELECT set_config('telixo.audit_retention_purge', 'authorized', true)", [])

        Postgrex.query!(
          conn,
          """
          INSERT INTO telixo_audit_retention_archives
            (archive_id, tenant_id, first_sequence, last_sequence, event_count,
             archive_sha256, archive_uri, actor_id, reason, request_id)
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
          """,
          [archive_id, tenant_id, first_sequence, last_sequence, length(events),
           archive_hash, Path.expand(archive_path), actor_id, reason, request_id]
        )

        Postgrex.query!(
          conn,
          """
          INSERT INTO telixo_audit_chain_anchors
            (tenant_id, first_retained_sequence, previous_hash, archived_through_sequence, archive_sha256)
          VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (tenant_id) DO UPDATE
            SET first_retained_sequence = EXCLUDED.first_retained_sequence,
                previous_hash = EXCLUDED.previous_hash,
                archived_through_sequence = EXCLUDED.archived_through_sequence,
                archive_sha256 = EXCLUDED.archive_sha256,
                updated_at = now()
          WHERE telixo_audit_chain_anchors.archived_through_sequence < EXCLUDED.archived_through_sequence
          """,
          [tenant_id, last_sequence + 1, last_hash, last_sequence, archive_hash]
        )

        Postgrex.query!(
          conn,
          """
          INSERT INTO telixo_audit_privileged_access_log
            (access_id, tenant_id, actor_id, action, reason, request_id)
          VALUES ($1, $2, $3, 'audit.retention_purge', $4, $5)
          """,
          [random_id(), tenant_id, actor_id, reason, request_id]
        )

        delete_result =
          Postgrex.query!(
            conn,
            """
            DELETE FROM telixo_audit_events
            WHERE tenant_id = $1 AND tenant_sequence BETWEEN $2 AND $3 AND recorded_at < $4
            """,
            [tenant_id, first_sequence, last_sequence, current_cutoff]
          )

        unless delete_result.num_rows == length(events) do
          raise "Database retention guard blocked deletion; expected #{length(events)} rows, deleted #{delete_result.num_rows}"
        end

        delete_result.num_rows
      end)

    case result do
      {:ok, count} ->
        Mix.shell().info("Archived and purged #{count} audit events for tenant #{tenant_id}; sha256=#{archive_hash}")

      {:error, error} ->
        Mix.raise("Audit retention transaction failed for tenant #{tenant_id}: #{inspect(error)}")
    end
  end

  defp verify_chain_rows([], _tenant_id, _expected_sequence, _previous_hash), do: :ok

  defp verify_chain_rows(
         [row | rest],
         tenant_id,
         expected_sequence,
         expected_previous_hash
       ) do
    event_id = Enum.at(row, 0)
    sequence = Enum.at(row, 2)
    idempotency_key = Enum.at(row, 3)
    payload = Jason.decode!(Enum.at(row, 7))
    previous_hash = Enum.at(row, 8)
    stored_hash = Enum.at(row, 9)
    expected_hash = calculate_hash(tenant_id, idempotency_key, sequence, payload, expected_previous_hash)

    if sequence == expected_sequence and previous_hash == expected_previous_hash and
         is_binary(stored_hash) and Plug.Crypto.secure_compare(stored_hash, expected_hash) do
      verify_chain_rows(rest, tenant_id, expected_sequence + 1, stored_hash)
    else
      {:error, event_id}
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

  defp encode_event(row) do
    event = %{
      "event_id" => Enum.at(row, 0),
      "tenant_id" => Enum.at(row, 1),
      "tenant_sequence" => Enum.at(row, 2),
      "idempotency_key" => Enum.at(row, 3),
      "actor_type" => Enum.at(row, 4),
      "action" => Enum.at(row, 5),
      "occurred_at" => DateTime.to_iso8601(Enum.at(row, 6)),
      "event" => Jason.decode!(Enum.at(row, 7)),
      "previous_hash" => Enum.at(row, 8),
      "event_hash" => Enum.at(row, 9),
      "recorded_at" => DateTime.to_iso8601(Enum.at(row, 10))
    }

    Jason.encode!(event)
  end

  defp database_user(url) do
    case URI.parse(url).userinfo do
      nil -> nil
      userinfo -> userinfo |> String.split(":", parts: 2) |> hd()
    end
  end

  defp random_id, do: Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)
end
