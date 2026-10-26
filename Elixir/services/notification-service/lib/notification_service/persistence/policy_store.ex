defmodule PesaGuard.NotificationService.Persistence.PolicyStore do
  @moduledoc """
  Authoritative, tenant-scoped consent, channel-preference, and suppression store.

  Mutation functions are internal service APIs: do not expose them through a
  tenant-facing controller without a separate privileged internal identity and
  authorization policy. Policy reads fail closed when persistence is unavailable.
  """

  @connection PesaGuard.NotificationService.Persistence.PostgresConnection

  alias PesaGuard.NotificationService.Domain.DispatchPolicy

  @channels ~w(email sms in_app)

  def authorize(tenant_id, intent)
      when is_binary(tenant_id) and is_map(intent) do
    recipient = Map.get(intent, "recipient_ref")
    channel = Map.get(intent, "channel")
    purpose = Map.get(intent, "purpose")

    cond do
      not non_empty?(recipient) -> {:error, :recipient_ref_required}
      channel not in @channels -> {:error, :unsupported_channel}
      not non_empty?(purpose) -> {:error, :consent_purpose_missing}
      true -> load_and_authorize(tenant_id, recipient, channel, purpose, intent)
    end
  end

  def authorize(_, _), do: {:error, :invalid_policy_context}

  def record_consent(tenant_id, recipient_ref, purpose, granted, source, updated_by)
      when is_binary(tenant_id) and is_binary(recipient_ref) and is_binary(purpose) and
             is_boolean(granted) and is_binary(source) and is_binary(updated_by) do
    with :ok <- validate_identifiers([tenant_id, recipient_ref, purpose, source, updated_by]) do
      transaction_with_event(
        tenant_id,
        "notification-policy.consent_changed",
        %{"recipient_ref" => recipient_ref, "purpose" => purpose, "granted" => granted, "source" => source},
        fn conn ->
          Postgrex.query!(conn, """
          INSERT INTO telixo_notification_consents
            (tenant_id, recipient_ref, purpose, granted, source, updated_by)
          VALUES ($1, $2, $3, $4, $5, $6)
          ON CONFLICT (tenant_id, recipient_ref, purpose) DO UPDATE
            SET granted = EXCLUDED.granted, source = EXCLUDED.source,
                updated_by = EXCLUDED.updated_by, updated_at = now()
          """, [tenant_id, recipient_ref, purpose, granted, source, updated_by])
        end
      )
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  end

  def set_preference(tenant_id, recipient_ref, channel, enabled, updated_by)
      when is_binary(tenant_id) and is_binary(recipient_ref) and channel in @channels and
             is_boolean(enabled) and is_binary(updated_by) do
    with :ok <- validate_identifiers([tenant_id, recipient_ref, channel, updated_by]) do
      transaction_with_event(
        tenant_id,
        "notification-policy.preference_changed",
        %{"recipient_ref" => recipient_ref, "channel" => channel, "enabled" => enabled},
        fn conn ->
          Postgrex.query!(conn, """
          INSERT INTO telixo_notification_preferences
            (tenant_id, recipient_ref, channel, enabled, updated_by)
          VALUES ($1, $2, $3, $4, $5)
          ON CONFLICT (tenant_id, recipient_ref, channel) DO UPDATE
            SET enabled = EXCLUDED.enabled, updated_by = EXCLUDED.updated_by, updated_at = now()
          """, [tenant_id, recipient_ref, channel, enabled, updated_by])
        end
      )
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  end

  def suppress(tenant_id, recipient_ref, reason_code, created_by)
      when is_binary(tenant_id) and is_binary(recipient_ref) and is_binary(reason_code) and
             is_binary(created_by) do
    with :ok <- validate_identifiers([tenant_id, recipient_ref, reason_code, created_by]) do
      transaction_with_event(
        tenant_id,
        "notification-policy.recipient_suppressed",
        %{"recipient_ref" => recipient_ref, "reason_code" => reason_code},
        fn conn ->
          Postgrex.query!(conn, """
          INSERT INTO telixo_notification_suppressions
            (tenant_id, recipient_ref, reason_code, created_by)
          VALUES ($1, $2, $3, $4)
          ON CONFLICT (tenant_id, recipient_ref) DO UPDATE
            SET reason_code = EXCLUDED.reason_code, created_by = EXCLUDED.created_by,
                created_at = now()
          """, [tenant_id, recipient_ref, reason_code, created_by])
        end
      )
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  end

  def unsuppress(tenant_id, recipient_ref, changed_by)
      when is_binary(tenant_id) and is_binary(recipient_ref) and is_binary(changed_by) do
    with :ok <- validate_identifiers([tenant_id, recipient_ref, changed_by]) do
      transaction_with_event(
        tenant_id,
        "notification-policy.recipient_unsuppressed",
        %{"recipient_ref" => recipient_ref},
        fn conn ->
          Postgrex.query!(conn, """
          DELETE FROM telixo_notification_suppressions
          WHERE tenant_id = $1 AND recipient_ref = $2
          """, [tenant_id, recipient_ref])
        end
      )
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  end

  defp load_and_authorize(tenant_id, recipient, channel, purpose, intent) do
    sql = """
    SELECT c.granted, c.purpose, p.enabled,
      EXISTS (
        SELECT 1 FROM telixo_notification_suppressions s
        WHERE s.tenant_id = $1 AND s.recipient_ref = $2
      ) AS suppressed
    FROM (SELECT 1) request
    LEFT JOIN telixo_notification_consents c
      ON c.tenant_id = $1 AND c.recipient_ref = $2 AND c.purpose = $4
    LEFT JOIN telixo_notification_preferences p
      ON p.tenant_id = $1 AND p.recipient_ref = $2 AND p.channel = $3
    """

    case Postgrex.query(@connection, sql, [tenant_id, recipient, channel, purpose]) do
      {:ok, %{rows: [[granted, stored_purpose, enabled, suppressed]]}} ->
        consent =
          if is_nil(granted),
            do: nil,
            else: %{granted: granted, purpose: stored_purpose}

        context = %{
          consent: consent,
          channel_enabled: enabled === true,
          suppressed: suppressed === true
        }

        DispatchPolicy.authorize(intent, context)

      {:ok, _} ->
        {:error, :policy_record_unavailable}

      {:error, _} ->
        {:error, :policy_store_unavailable}
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  catch
    :exit, _ -> {:error, :policy_store_unavailable}
  end

  defp transaction_with_event(tenant_id, event_type, payload, mutation) do
    event_id = Base.url_encode64(:crypto.strong_rand_bytes(18), padding: false)

    case Postgrex.transaction(@connection, fn conn ->
           mutation.(conn)

           event = %{
             "event_id" => event_id,
             "tenant_id" => tenant_id,
             "event_type" => event_type,
             "occurred_at" => DateTime.utc_now() |> DateTime.to_iso8601(),
             "schema_version" => 1,
             "payload" => payload
           }

           Postgrex.query!(conn, """
           INSERT INTO telixo_outbox (event_id, service_name, tenant_id, event_type, payload)
           VALUES ($1, 'notification-service', $2, $3, $4::text::jsonb)
           """, [event_id, tenant_id, event_type, Jason.encode!(event)])
         end) do
      {:ok, _} -> :ok
      {:error, _} -> {:error, :policy_store_unavailable}
    end
  rescue
    _ -> {:error, :policy_store_unavailable}
  end

  defp validate_identifiers(values) do
    if Enum.all?(values, &(is_binary(&1) and byte_size(&1) in 1..256)),
      do: :ok,
      else: {:error, :invalid_policy_record}
  end

  defp non_empty?(value), do: is_binary(value) and String.trim(value) != ""
end
