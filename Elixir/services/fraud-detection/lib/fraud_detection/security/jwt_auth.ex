defmodule PesaGuard.FraudDetection.Security.JWTAuth do
  @moduledoc "Fail-closed HS256 bearer-token verification for tenant-scoped APIs."

  import Plug.Conn

  @issuer "telixo"
  @audience "telixo"

  def init(opts), do: opts

  def call(conn, _opts) do
    secret = System.get_env("JWT_SECRET")

    cond do
      not is_binary(secret) or byte_size(secret) < 32 ->
        unauthorized(conn, "authentication_unavailable", 503)

      true ->
        case get_req_header(conn, "authorization") do
          ["Bearer " <> token] ->
            case verify_token(token, secret, System.get_env("JWT_ISSUER", @issuer)) do
              {:ok, claims} ->
                assign(conn, :tenant_context, %{
                  tenant_id: claims["tenant_id"],
                  subject: claims["sub"],
                  claims: claims
                })

              {:error, _reason} ->
                unauthorized(conn, "invalid_token", 401)
            end

          _ ->
            unauthorized(conn, "missing_bearer_token", 401)
        end
    end
  end

  @spec verify_token(binary(), binary(), binary()) :: {:ok, map()} | {:error, atom()}
  def verify_token(token, secret, issuer)
      when is_binary(token) and byte_size(token) <= 8_192 and is_binary(secret) and
             byte_size(secret) >= 32 and is_binary(issuer) do
    with [encoded_header, encoded_claims, encoded_signature] <- String.split(token, "."),
         {:ok, header_json} <- Base.url_decode64(encoded_header, padding: false),
         {:ok, header} when is_map(header) <- Jason.decode(header_json),
         true <- Map.get(header, "alg") == "HS256",
         {:ok, claims_json} <- Base.url_decode64(encoded_claims, padding: false),
         {:ok, claims} when is_map(claims) <- Jason.decode(claims_json),
         {:ok, signature} <- Base.url_decode64(encoded_signature, padding: false),
         expected <- :crypto.mac(:hmac, :sha256, secret, encoded_header <> "." <> encoded_claims),
         true <- byte_size(signature) == byte_size(expected) and Plug.Crypto.secure_compare(signature, expected),
         :ok <- validate_claims(claims, issuer) do
      {:ok, claims}
    else
      false -> {:error, :invalid_signature_or_claim}
      {:error, _} -> {:error, :invalid_token}
      _ -> {:error, :invalid_token}
    end
  end

  def verify_token(_, _, _), do: {:error, :invalid_token}

  defp validate_claims(claims, issuer) do
    now = System.system_time(:second)
    audience = Map.get(claims, "aud")

    cond do
      not is_binary(Map.get(claims, "tenant_id")) or Map.get(claims, "tenant_id") == "" ->
        {:error, :missing_tenant}

      not is_binary(Map.get(claims, "sub")) or Map.get(claims, "sub") == "" ->
        {:error, :missing_subject}

      Map.get(claims, "iss") != issuer ->
        {:error, :invalid_issuer}

      not (audience == @audience or (is_list(audience) and @audience in audience)) ->
        {:error, :invalid_audience}

      not is_integer(Map.get(claims, "exp")) or Map.get(claims, "exp") <= now ->
        {:error, :expired}

      is_integer(Map.get(claims, "nbf")) and Map.get(claims, "nbf") > now ->
        {:error, :not_yet_valid}

      true ->
        :ok
    end
  end

  defp unauthorized(conn, error, status) do
    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, Jason.encode!(%{error: error}))
    |> halt()
  end
end
