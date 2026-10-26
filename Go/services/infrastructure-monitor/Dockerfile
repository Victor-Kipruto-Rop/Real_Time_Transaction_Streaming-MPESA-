FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/infrastructure-monitor .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/infrastructure-monitor /infrastructure-monitor
USER nonroot:nonroot
EXPOSE 8083
ENTRYPOINT ["/infrastructure-monitor"]
