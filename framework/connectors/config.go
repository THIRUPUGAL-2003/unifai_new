package connectors

// ConnectorNames lists workspace data connector identifiers.
var ConnectorNames = []string{"datadog", "kafka", "bigquery", "pubsub"}

// Settings is the runtime view of a saved connector row.
type Settings struct {
	Name    string
	Enabled bool
	Config  map[string]string
}
