package tables

import (
	"time"
)

// TableUser represents a custom user record stored in PostgreSQL
type TableUser struct {
	ID        string    `gorm:"primaryKey;type:varchar(255)" json:"id"`
	Username  string    `gorm:"type:varchar(255);uniqueIndex;not null" json:"username"`
	Password  string    `gorm:"type:text;not null" json:"password"`
	Role      string    `gorm:"type:varchar(50);not null" json:"role"` // "admin" or "user"
	Budget    float64   `json:"budget"` // Cost limit in USD
	RateLimit int       `json:"rate_limit"` // Requests per minute (RPM)
	AllowedPromptRepos string    `gorm:"type:text" json:"allowed_prompt_repos"` // Comma-separated allowed prompt IDs
	CreatedAt          time.Time `json:"created_at"`
	UpdatedAt          time.Time `json:"updated_at"`
}

// TableName returns the table name for custom users
func (TableUser) TableName() string {
	return "governance_users"
}
