package postgresconn

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/unifai/unifai/core/schemas"
	"github.com/stretchr/testify/require"
	gormlogger "gorm.io/gorm/logger"
)

func TestPasswordCommandOpensRealPostgresConnections(t *testing.T) {
	if os.Getenv("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST") != "1" {
		t.Skip("set UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST=1 to run against local Postgres")
	}

	password := getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_PASSWORD", "unifai_password")
	dir := t.TempDir()
	counterPath := filepath.Join(dir, "password-command-count")
	scriptPath := filepath.Join(dir, "password-command.sh")
	script := fmt.Sprintf("#!/bin/sh\nprintf 'called\\n' >> %q\nprintf %%s %q\n", counterPath, password)
	require.NoError(t, os.WriteFile(scriptPath, []byte(script), 0o700))

	cfg := &Config{
		Host:            schemas.NewSecretVar(getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_HOST", "localhost")),
		Port:            schemas.NewSecretVar(getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_PORT", "5432")),
		User:            schemas.NewSecretVar(getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_USER", "unifai")),
		DBName:          schemas.NewSecretVar(getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_DB", "unifai")),
		SSLMode:         schemas.NewSecretVar(getenvDefault("UNIFAI_POSTGRES_PASSWORD_COMMAND_TEST_SSLMODE", "disable")),
		PasswordCommand: &PasswordCommandConfig{Command: scriptPath, Timeout: "5s"},
	}

	require.NoError(t, Validate(cfg, true))
	db, err := Open(BuildDSN(cfg), cfg, gormlogger.Default)
	require.NoError(t, err)
	sqlDB, err := db.DB()
	require.NoError(t, err)
	defer sqlDB.Close()

	sqlDB.SetMaxOpenConns(1)
	sqlDB.SetMaxIdleConns(0)

	require.NoError(t, db.Exec("SELECT 1").Error)
	time.Sleep(10 * time.Millisecond)
	require.NoError(t, db.Exec("SELECT 1").Error)

	raw, err := os.ReadFile(counterPath)
	require.NoError(t, err)
	require.GreaterOrEqual(t, strings.Count(string(raw), "called"), 2)
}

func getenvDefault(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
