FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/quota-engine .

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/quota-engine /quota-engine
USER nonroot:nonroot
EXPOSE 8082
ENTRYPOINT ["/quota-engine"]
