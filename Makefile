# sigma-quant — Autonomous Strategy Research Factory
# Build commands for development and distribution

# Variables
BINARY_NAME := sigma-quant
MODULE := github.com/Dallionking/sigma-quant-stream
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')
LDFLAGS := -s -w -X $(MODULE)/internal/cmd.Version=$(VERSION) -X $(MODULE)/internal/cmd.GitCommit=$(COMMIT) -X $(MODULE)/internal/cmd.BuildDate=$(BUILD_TIME)

.PHONY: build run install clean test lint fmt vet tidy dev help

## Build
build:                    ## Build the binary
	go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME) ./cmd/sigma-quant

build-all:                ## Build for all platforms
	GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-arm64 ./cmd/sigma-quant
	GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-darwin-amd64 ./cmd/sigma-quant
	GOOS=linux GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-linux-amd64 ./cmd/sigma-quant
	GOOS=linux GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(BINARY_NAME)-linux-arm64 ./cmd/sigma-quant

## Development
run:                      ## Run in development mode
	go run ./cmd/sigma-quant $(ARGS)

dev:                      ## Run with hot reload (requires air)
	air

install:                  ## Install to GOPATH/bin
	go install -ldflags "$(LDFLAGS)" ./cmd/sigma-quant

## Testing
test:                     ## Run tests
	go test -v -race -count=1 ./...

test-cover:               ## Run tests with coverage
	go test -v -race -coverprofile=coverage.out ./...
	go tool cover -html=coverage.out -o coverage.html

## Quality
lint:                     ## Run linter (requires golangci-lint)
	golangci-lint run ./...

fmt:                      ## Format code
	gofumpt -l -w .

vet:                      ## Run go vet
	go vet ./...

## Dependencies
tidy:                     ## Tidy dependencies
	go mod tidy

## Cleanup
clean:                    ## Remove build artifacts
	rm -rf bin/ coverage.out coverage.html

## Python deps (for backtest runner)
setup-python:             ## Install Python dependencies
	pip install -r requirements.txt 2>/dev/null || pip install pandas pandas-ta ccxt pydantic typer rich

## Help
help:                     ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
