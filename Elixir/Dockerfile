FROM hexpm/elixir:1.17.3-erlang-27.1-debian-bookworm-20241016 AS build
WORKDIR /app
RUN mix local.hex --force && mix local.rebar --force
ARG SERVICE
COPY Elixir/services/${SERVICE}/mix.exs ./
RUN mix deps.get
COPY Elixir/services/${SERVICE}/ ./
ENV MIX_ENV=prod
RUN mix deps.compile && mix compile
CMD ["sh","-c","mix run --no-halt"]
