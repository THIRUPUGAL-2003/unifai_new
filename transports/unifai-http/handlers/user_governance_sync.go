package handlers

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/unifai/unifai/framework/configstore/tables"
)

// UserGovernanceSyncer pushes materialized user budget/rate-limit rows into the
// governance in-memory store so enforcement picks them up without a restart.
type UserGovernanceSyncer interface {
	SyncUserGovernance(ctx context.Context, userID string, budget *tables.TableBudget, rateLimit *tables.TableRateLimit)
	DeleteUserGovernance(ctx context.Context, userID string)
}

const (
	userBudgetResetDuration = "1M"
	userRateLimitReset      = "1m"
)

// materializeUserGovernanceLimits turns Users.Budget / Users.RateLimit UI fields
// into live TableBudget / TableRateLimit rows owned by the user, then syncs memory.
func (h *SessionHandler) materializeUserGovernanceLimits(ctx context.Context, user *tables.TableUser) error {
	if h == nil || h.configStore == nil || user == nil || user.ID == "" {
		return nil
	}
	now := time.Now().UTC()
	uid := user.ID

	var budget *tables.TableBudget
	if user.Budget > 0 {
		if user.BudgetID != nil && *user.BudgetID != "" {
			existing, err := h.configStore.GetBudget(ctx, *user.BudgetID)
			if err == nil && existing != nil {
				existing.MaxLimit = user.Budget
				existing.ResetDuration = userBudgetResetDuration
				existing.UserID = &uid
				existing.UpdatedAt = now
				if err := h.configStore.UpdateBudget(ctx, existing); err != nil {
					return err
				}
				budget = existing
			}
		}
		if budget == nil {
			bid := uuid.New().String()
			budget = &tables.TableBudget{
				ID:            bid,
				MaxLimit:      user.Budget,
				ResetDuration: userBudgetResetDuration,
				LastReset:     now,
				CurrentUsage:  0,
				UserID:        &uid,
				CreatedAt:     now,
				UpdatedAt:     now,
			}
			if err := h.configStore.CreateBudget(ctx, budget); err != nil {
				return err
			}
			user.BudgetID = &bid
		}
	} else if user.BudgetID != nil && *user.BudgetID != "" {
		_ = h.configStore.DeleteBudget(ctx, *user.BudgetID)
		user.BudgetID = nil
	}

	var rateLimit *tables.TableRateLimit
	if user.RateLimit > 0 {
		maxReq := int64(user.RateLimit)
		reset := userRateLimitReset
		if user.RateLimitID != nil && *user.RateLimitID != "" {
			existing, err := h.configStore.GetRateLimit(ctx, *user.RateLimitID)
			if err == nil && existing != nil {
				existing.RequestMaxLimit = &maxReq
				existing.RequestResetDuration = &reset
				existing.UpdatedAt = now
				if err := h.configStore.UpdateRateLimit(ctx, existing); err != nil {
					return err
				}
				rateLimit = existing
			}
		}
		if rateLimit == nil {
			rid := uuid.New().String()
			rateLimit = &tables.TableRateLimit{
				ID:                   rid,
				RequestMaxLimit:      &maxReq,
				RequestResetDuration: &reset,
				RequestLastReset:     now,
				TokenLastReset:       now,
				CreatedAt:            now,
				UpdatedAt:            now,
			}
			if err := h.configStore.CreateRateLimit(ctx, rateLimit); err != nil {
				return err
			}
			user.RateLimitID = &rid
		}
	} else if user.RateLimitID != nil && *user.RateLimitID != "" {
		_ = h.configStore.DeleteRateLimit(ctx, *user.RateLimitID)
		user.RateLimitID = nil
	}

	if h.userGovernance != nil {
		if budget == nil && rateLimit == nil {
			h.userGovernance.DeleteUserGovernance(ctx, user.ID)
		} else {
			h.userGovernance.SyncUserGovernance(ctx, user.ID, budget, rateLimit)
		}
	}
	return nil
}
