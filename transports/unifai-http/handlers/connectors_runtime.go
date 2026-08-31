package handlers

import (
	"context"

	"github.com/unifai/unifai/framework/configstore"
	"github.com/unifai/unifai/framework/connectors"
)

// ReloadConnectorsFromStore refreshes connector runtime settings from the workspace DB.
func ReloadConnectorsFromStore(store configstore.WorkspaceStore) {
	if store == nil {
		return
	}
	_ = connectors.ReloadFromStore(context.Background(), store)
}
