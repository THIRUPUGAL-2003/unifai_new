package cluster

import (
	"sync"

	"github.com/unifai/unifai/framework/kvstore"
)

// SyncDelegate bridges cluster config to the in-memory KV store.
type SyncDelegate struct {
	mu      sync.Mutex
	enabled bool
}

// Runtime is the process-wide cluster sync runtime.
var Runtime = &SyncDelegate{}

// Apply enables or disables KV replication hooks.
func (r *SyncDelegate) Apply(enabled bool, store *kvstore.Store) {
	r.mu.Lock()
	r.enabled = enabled
	r.mu.Unlock()
	if store == nil {
		return
	}
	if enabled {
		store.SetDelegate(r)
		return
	}
	store.SetDelegate(nil)
}

func (r *SyncDelegate) OnSet(key string, valueJSON []byte, writtenAt int64, expiresAt int64) {
	r.mu.Lock()
	enabled := r.enabled
	r.mu.Unlock()
	if !enabled {
		return
	}
	_ = key
	_ = valueJSON
	_ = writtenAt
	_ = expiresAt
}

func (r *SyncDelegate) OnDelete(key string, deletedAt int64) {
	r.mu.Lock()
	enabled := r.enabled
	r.mu.Unlock()
	if !enabled {
		return
	}
	_ = key
	_ = deletedAt
}
