FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/event-relay .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/event-relay /event-relay
USER nonroot:nonroot
EXPOSE 8081
ENTRYPOINT ["/event-relay"]
