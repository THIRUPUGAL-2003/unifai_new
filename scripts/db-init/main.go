package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	unifai "github.com/unifai/unifai/core"
	"github.com/unifai/unifai/core/schemas"
	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/logstore"
)

type fileConfig struct {
	ConfigStore configstore.Config `json:"config_store"`
	LogsStore   logstore.Config    `json:"logs_store"`
}

func main() {
	configPath := flag.String("config", "config.json", "path to config.json")
	flag.Parse()

	abs, err := filepath.Abs(*configPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config path: %v\n", err)
		os.Exit(1)
	}

	data, err := os.ReadFile(abs)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read config: %v\n", err)
		os.Exit(1)
	}

	var cfg fileConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		fmt.Fprintf(os.Stderr, "parse config: %v\n", err)
		os.Exit(1)
	}

	logger := unifai.NewDefaultLogger(schemas.LogLevelInfo)
	ctx := context.Background()

	fmt.Println("==> Running config_store migrations...")
	cs, err := configstore.NewConfigStore(ctx, &cfg.ConfigStore, logger)
	if err != nil {
		fmt.Fprintf(os.Stderr, "config_store failed: %v\n", err)
		os.Exit(1)
	}
	if cs != nil {
		cs.Close(ctx)
	}
	fmt.Println("==> config_store migrations complete")

	fmt.Println("==> Running logs_store migrations...")
	ls, err := logstore.NewLogStore(ctx, &cfg.LogsStore, logger)
	if err != nil {
		fmt.Fprintf(os.Stderr, "logs_store failed: %v\n", err)
		os.Exit(1)
	}
	if ls != nil {
		ls.Close(ctx)
	}
	fmt.Println("==> logs_store migrations complete")
	fmt.Println("Done. Refresh Tables in pgAdmin.")
}
