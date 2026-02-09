package main

import (
	"os"

	"github.com/Dallionking/sigma-quant-stream/internal/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}
