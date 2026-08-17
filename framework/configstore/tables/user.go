package tables

import (
	"time"
)

// User registration / approval statuses.
const (
	UserStatusPending  = "pending"
	UserStatusApproved = "approved"
	UserStatusRejected = "rejected"
)

// TableUser represents a custom user record stored in PostgreSQL
type TableUser struct {
	ID                 string     `gorm:"primaryKey;type:varchar(255)" json:"id"`
	Username           string     `gorm:"type:varchar(255);uniqueIndex;not null" json:"username"`
	Email              string     `gorm:"type:varchar(255);index" json:"email"`
	Password           string     `gorm:"type:text;not null" json:"password"`
	Role               string     `gorm:"type:varchar(50);not null" json:"role"`     // "admin" or "user"
	Status             string     `gorm:"type:varchar(50);not null;default:approved;index" json:"status"` // pending | approved | rejected
	Budget             float64    `json:"budget"`                                                          // Cost limit in USD
	RateLimit          int        `json:"rate_limit"`                                                      // Requests per minute (RPM)
	AllowedPromptRepos string     `gorm:"type:text" json:"allowed_prompt_repos"`                           // Comma-separated allowed prompt IDs
	ReviewedAt         *time.Time `json:"reviewed_at,omitempty"`
	CreatedAt          time.Time  `json:"created_at"`
	UpdatedAt          time.Time  `json:"updated_at"`
}

// TableName returns the table name for custom users
func (TableUser) TableName() string {
	return "governance_users"
}

// IsApproved reports whether the user may log in.
func (u *TableUser) IsApproved() bool {
	if u == nil {
		return false
	}
	s := u.Status
	if s == "" {
		return true // legacy rows before status column
	}
	return s == UserStatusApproved
}
