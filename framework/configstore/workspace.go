package configstore

import (
	"context"
	"errors"
	"time"

	"github.com/unifai/unifai/framework/configstore/tables"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

const (
	WorkspaceSettingCluster      = "cluster"
	WorkspaceSettingLoadBalancer = "load_balancer"
	WorkspaceSettingSCIM         = "scim"
	WorkspaceSettingAudit        = "audit"
)

func WorkspaceSettingConnector(name string) string {
	return "connector:" + name
}

// AuditLogQuery filters persisted administrative mutations.
type AuditLogQuery struct {
	Search  string
	Action  string
	Outcome string
	Start   *time.Time
	End     *time.Time
	Limit   int
	Offset  int
}

// WorkspaceStore is the persistence surface for workspace features
// (access profiles, RBAC, circuit breaker, audit logs, and related pages).
// RDBConfigStore implements it. File-backed ConfigStore does not.
type WorkspaceStore interface {
	ListAccessProfiles(ctx context.Context) ([]tables.TableAccessProfile, error)
	GetAccessProfile(ctx context.Context, id uint) (*tables.TableAccessProfile, error)
	CreateAccessProfile(ctx context.Context, row *tables.TableAccessProfile) error
	UpdateAccessProfile(ctx context.Context, row *tables.TableAccessProfile) error
	DeleteAccessProfile(ctx context.Context, id uint) error

	ListRBACRoles(ctx context.Context) ([]tables.TableRBACRole, error)
	GetRBACRole(ctx context.Context, id uint) (*tables.TableRBACRole, error)
	CreateRBACRole(ctx context.Context, row *tables.TableRBACRole) error
	UpdateRBACRole(ctx context.Context, row *tables.TableRBACRole) error
	DeleteRBACRole(ctx context.Context, id uint) error
	EnsureRBACRoles(ctx context.Context) error

	ListBusinessUnits(ctx context.Context) ([]tables.TableBusinessUnit, error)
	GetBusinessUnit(ctx context.Context, id string) (*tables.TableBusinessUnit, error)
	CreateBusinessUnit(ctx context.Context, row *tables.TableBusinessUnit) error
	UpdateBusinessUnit(ctx context.Context, row *tables.TableBusinessUnit) error
	DeleteBusinessUnit(ctx context.Context, id string) error

	ListAlertChannels(ctx context.Context) ([]tables.TableAlertChannel, error)
	GetAlertChannel(ctx context.Context, id uint) (*tables.TableAlertChannel, error)
	CreateAlertChannel(ctx context.Context, row *tables.TableAlertChannel) error
	UpdateAlertChannel(ctx context.Context, row *tables.TableAlertChannel) error
	DeleteAlertChannel(ctx context.Context, id uint) error

	ListCircuitBreakerPolicies(ctx context.Context) ([]tables.TableCircuitBreakerPolicy, error)
	GetCircuitBreakerPolicy(ctx context.Context, name string) (*tables.TableCircuitBreakerPolicy, error)
	CreateCircuitBreakerPolicy(ctx context.Context, row *tables.TableCircuitBreakerPolicy) error
	UpdateCircuitBreakerPolicy(ctx context.Context, row *tables.TableCircuitBreakerPolicy) error
	DeleteCircuitBreakerPolicy(ctx context.Context, name string) error

	ListMCPToolGroups(ctx context.Context) ([]tables.TableMCPToolGroup, error)
	GetMCPToolGroup(ctx context.Context, id uint) (*tables.TableMCPToolGroup, error)
	CreateMCPToolGroup(ctx context.Context, row *tables.TableMCPToolGroup) error
	UpdateMCPToolGroup(ctx context.Context, row *tables.TableMCPToolGroup) error
	DeleteMCPToolGroup(ctx context.Context, id uint) error

	ListPromptDeployments(ctx context.Context, promptID string) ([]tables.TablePromptDeployment, error)
	GetPromptDeployment(ctx context.Context, id uint) (*tables.TablePromptDeployment, error)
	CreatePromptDeployment(ctx context.Context, row *tables.TablePromptDeployment) error
	UpdatePromptDeployment(ctx context.Context, row *tables.TablePromptDeployment) error
	DeletePromptDeployment(ctx context.Context, id uint) error

	ListVirtualKeyUsers(ctx context.Context, virtualKeyID string) ([]tables.TableVirtualKeyUser, error)
	SetVirtualKeyUser(ctx context.Context, virtualKeyID, userID string) error
	DeleteVirtualKeyUser(ctx context.Context, virtualKeyID string) error
	ListVirtualKeysForUser(ctx context.Context, userID string) ([]tables.TableVirtualKeyUser, error)

	GetWorkspaceSetting(ctx context.Context, key string) (*tables.TableWorkspaceSetting, error)
	UpsertWorkspaceSetting(ctx context.Context, key, data string) error

	ListAuditLogs(ctx context.Context, query AuditLogQuery) ([]tables.TableAuditLog, int64, error)
	CreateAuditLog(ctx context.Context, row *tables.TableAuditLog) error
}

// AsWorkspaceStore returns the workspace persistence layer when the config
// store is an RDB implementation.
func AsWorkspaceStore(store ConfigStore) (WorkspaceStore, bool) {
	if store == nil {
		return nil, false
	}
	ws, ok := store.(WorkspaceStore)
	return ws, ok
}

func (s *RDBConfigStore) ListAccessProfiles(ctx context.Context) ([]tables.TableAccessProfile, error) {
	var rows []tables.TableAccessProfile
	err := s.DB().WithContext(ctx).Order("id asc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetAccessProfile(ctx context.Context, id uint) (*tables.TableAccessProfile, error) {
	return firstByID[tables.TableAccessProfile](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) CreateAccessProfile(ctx context.Context, row *tables.TableAccessProfile) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateAccessProfile(ctx context.Context, row *tables.TableAccessProfile) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteAccessProfile(ctx context.Context, id uint) error {
	return deleteByID[tables.TableAccessProfile](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) ListRBACRoles(ctx context.Context) ([]tables.TableRBACRole, error) {
	var rows []tables.TableRBACRole
	err := s.DB().WithContext(ctx).Order("id asc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetRBACRole(ctx context.Context, id uint) (*tables.TableRBACRole, error) {
	return firstByID[tables.TableRBACRole](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) CreateRBACRole(ctx context.Context, row *tables.TableRBACRole) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateRBACRole(ctx context.Context, row *tables.TableRBACRole) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteRBACRole(ctx context.Context, id uint) error {
	return deleteByID[tables.TableRBACRole](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) EnsureRBACRoles(ctx context.Context) error {
	var count int64
	if err := s.DB().WithContext(ctx).Model(&tables.TableRBACRole{}).Count(&count).Error; err != nil {
		return err
	}
	if count > 0 {
		return nil
	}
	now := time.Now().UTC()
	allIDs := make([]uint, 0, len(RBACPermissions()))
	readIDs := make([]uint, 0)
	for _, perm := range RBACPermissions() {
		allIDs = append(allIDs, perm.ID)
		if perm.Operation != "View" && perm.Operation != "Read" {
			continue
		}
		switch perm.Resource {
		case "Dashboard", "Logs", "Inference", "PromptRepository", "Observability", "MCPGateway":
			readIDs = append(readIDs, perm.ID)
		}
	}
	admin := tables.TableRBACRole{
		Name: "admin", Description: "Full workspace access", IsSystemRole: true,
		DAC: "all-data", ParsedPermissionIDs: allIDs, CreatedAt: now, UpdatedAt: now,
	}
	user := tables.TableRBACRole{
		Name: "user", Description: "Basic workspace access", IsSystemRole: true,
		DAC: "own-data", ParsedPermissionIDs: readIDs, CreatedAt: now, UpdatedAt: now,
	}
	return s.DB().WithContext(ctx).Create([]*tables.TableRBACRole{&admin, &user}).Error
}

func (s *RDBConfigStore) ListBusinessUnits(ctx context.Context) ([]tables.TableBusinessUnit, error) {
	var rows []tables.TableBusinessUnit
	err := s.DB().WithContext(ctx).Order("created_at desc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetBusinessUnit(ctx context.Context, id string) (*tables.TableBusinessUnit, error) {
	var row tables.TableBusinessUnit
	err := s.DB().WithContext(ctx).First(&row, "id = ?", id).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

func (s *RDBConfigStore) CreateBusinessUnit(ctx context.Context, row *tables.TableBusinessUnit) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateBusinessUnit(ctx context.Context, row *tables.TableBusinessUnit) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteBusinessUnit(ctx context.Context, id string) error {
	res := s.DB().WithContext(ctx).Where("id = ?", id).Delete(&tables.TableBusinessUnit{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

func (s *RDBConfigStore) ListAlertChannels(ctx context.Context) ([]tables.TableAlertChannel, error) {
	var rows []tables.TableAlertChannel
	err := s.DB().WithContext(ctx).Order("id asc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetAlertChannel(ctx context.Context, id uint) (*tables.TableAlertChannel, error) {
	return firstByID[tables.TableAlertChannel](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) CreateAlertChannel(ctx context.Context, row *tables.TableAlertChannel) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateAlertChannel(ctx context.Context, row *tables.TableAlertChannel) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteAlertChannel(ctx context.Context, id uint) error {
	return deleteByID[tables.TableAlertChannel](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) ListCircuitBreakerPolicies(ctx context.Context) ([]tables.TableCircuitBreakerPolicy, error) {
	var rows []tables.TableCircuitBreakerPolicy
	err := s.DB().WithContext(ctx).Order("name asc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetCircuitBreakerPolicy(ctx context.Context, name string) (*tables.TableCircuitBreakerPolicy, error) {
	var row tables.TableCircuitBreakerPolicy
	err := s.DB().WithContext(ctx).First(&row, "name = ?", name).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

func (s *RDBConfigStore) CreateCircuitBreakerPolicy(ctx context.Context, row *tables.TableCircuitBreakerPolicy) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateCircuitBreakerPolicy(ctx context.Context, row *tables.TableCircuitBreakerPolicy) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteCircuitBreakerPolicy(ctx context.Context, name string) error {
	res := s.DB().WithContext(ctx).Where("name = ?", name).Delete(&tables.TableCircuitBreakerPolicy{})
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

func (s *RDBConfigStore) ListMCPToolGroups(ctx context.Context) ([]tables.TableMCPToolGroup, error) {
	var rows []tables.TableMCPToolGroup
	err := s.DB().WithContext(ctx).Order("id asc").Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetMCPToolGroup(ctx context.Context, id uint) (*tables.TableMCPToolGroup, error) {
	return firstByID[tables.TableMCPToolGroup](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) CreateMCPToolGroup(ctx context.Context, row *tables.TableMCPToolGroup) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdateMCPToolGroup(ctx context.Context, row *tables.TableMCPToolGroup) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeleteMCPToolGroup(ctx context.Context, id uint) error {
	return deleteByID[tables.TableMCPToolGroup](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) ListPromptDeployments(ctx context.Context, promptID string) ([]tables.TablePromptDeployment, error) {
	query := s.DB().WithContext(ctx).Order("id asc")
	if promptID != "" {
		query = query.Where("prompt_id = ?", promptID)
	}
	var rows []tables.TablePromptDeployment
	err := query.Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) GetPromptDeployment(ctx context.Context, id uint) (*tables.TablePromptDeployment, error) {
	return firstByID[tables.TablePromptDeployment](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) CreatePromptDeployment(ctx context.Context, row *tables.TablePromptDeployment) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func (s *RDBConfigStore) UpdatePromptDeployment(ctx context.Context, row *tables.TablePromptDeployment) error {
	return s.DB().WithContext(ctx).Save(row).Error
}

func (s *RDBConfigStore) DeletePromptDeployment(ctx context.Context, id uint) error {
	return deleteByID[tables.TablePromptDeployment](s.DB().WithContext(ctx), id)
}

func (s *RDBConfigStore) ListVirtualKeyUsers(ctx context.Context, virtualKeyID string) ([]tables.TableVirtualKeyUser, error) {
	var rows []tables.TableVirtualKeyUser
	err := s.DB().WithContext(ctx).Where("virtual_key_id = ?", virtualKeyID).Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) ListVirtualKeysForUser(ctx context.Context, userID string) ([]tables.TableVirtualKeyUser, error) {
	var rows []tables.TableVirtualKeyUser
	err := s.DB().WithContext(ctx).Where("user_id = ?", userID).Find(&rows).Error
	return rows, err
}

func (s *RDBConfigStore) SetVirtualKeyUser(ctx context.Context, virtualKeyID, userID string) error {
	now := time.Now().UTC()
	var existing tables.TableVirtualKeyUser
	err := s.DB().WithContext(ctx).Where("virtual_key_id = ?", virtualKeyID).First(&existing).Error
	if err == nil {
		existing.UserID = userID
		existing.UpdatedAt = now
		return s.DB().WithContext(ctx).Save(&existing).Error
	}
	return s.DB().WithContext(ctx).Create(&tables.TableVirtualKeyUser{
		VirtualKeyID: virtualKeyID,
		UserID:       userID,
		CreatedAt:    now,
		UpdatedAt:    now,
	}).Error
}

func (s *RDBConfigStore) DeleteVirtualKeyUser(ctx context.Context, virtualKeyID string) error {
	return s.DB().WithContext(ctx).Where("virtual_key_id = ?", virtualKeyID).Delete(&tables.TableVirtualKeyUser{}).Error
}

func (s *RDBConfigStore) GetWorkspaceSetting(ctx context.Context, key string) (*tables.TableWorkspaceSetting, error) {
	var row tables.TableWorkspaceSetting
	err := s.DB().WithContext(ctx).First(&row, "key = ?", key).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

func (s *RDBConfigStore) UpsertWorkspaceSetting(ctx context.Context, key, data string) error {
	row := tables.TableWorkspaceSetting{Key: key, Data: data, UpdatedAt: time.Now().UTC()}
	return s.DB().WithContext(ctx).Clauses(clause.OnConflict{
		Columns:   []clause.Column{{Name: "key"}},
		DoUpdates: clause.AssignmentColumns([]string{"data", "updated_at"}),
	}).Create(&row).Error
}

func (s *RDBConfigStore) ListAuditLogs(ctx context.Context, query AuditLogQuery) ([]tables.TableAuditLog, int64, error) {
	db := s.DB().WithContext(ctx).Model(&tables.TableAuditLog{})
	if query.Search != "" {
		like := "%" + query.Search + "%"
		db = db.Where("LOWER(initiator) LIKE LOWER(?) OR LOWER(target) LIKE LOWER(?) OR LOWER(path) LIKE LOWER(?) OR LOWER(ip) LIKE LOWER(?)", like, like, like, like)
	}
	if query.Action != "" {
		db = db.Where("action = ?", query.Action)
	}
	if query.Outcome != "" {
		db = db.Where("outcome = ?", query.Outcome)
	}
	if query.Start != nil {
		db = db.Where("created_at >= ?", *query.Start)
	}
	if query.End != nil {
		db = db.Where("created_at <= ?", *query.End)
	}
	var total int64
	if err := db.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	limit := query.Limit
	if limit <= 0 || limit > 500 {
		limit = 50
	}
	var rows []tables.TableAuditLog
	err := db.Order("created_at desc").Limit(limit).Offset(query.Offset).Find(&rows).Error
	return rows, total, err
}

func (s *RDBConfigStore) CreateAuditLog(ctx context.Context, row *tables.TableAuditLog) error {
	return s.DB().WithContext(ctx).Create(row).Error
}

func firstByID[T any](db *gorm.DB, id uint) (*T, error) {
	var row T
	err := db.First(&row, id).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &row, nil
}

func deleteByID[T any](db *gorm.DB, id uint) error {
	var row T
	res := db.Delete(&row, id)
	if res.Error != nil {
		return res.Error
	}
	if res.RowsAffected == 0 {
		return ErrNotFound
	}
	return nil
}

// RBACPermission is a catalog entry. Permissions are code-declared, not stored.
type RBACPermission struct {
	ID        uint   `json:"id"`
	Resource  string `json:"resource"`
	Operation string `json:"operation"`
}

// RBACResourceNames is the workspace resource catalog.
var RBACResourceNames = []string{
	"GuardrailsConfig", "GuardrailsProviders", "GuardrailRules", "UserProvisioning", "Cluster",
	"Settings", "Users", "Logs", "Observability", "Dashboard", "VirtualKeys", "ModelProvider",
	"Plugins", "MCPGateway", "MCPToolGroups", "MCPLogs", "AdaptiveRouter", "AuditLogs",
	"Customers", "Teams", "RBAC", "Governance", "RoutingRules", "PromptRepository",
	"PromptDeploymentStrategy", "SkillsRepository", "AccessProfiles", "APIKeys",
	"Inference", "Metrics", "FeatureFlags", "CircuitBreaker",
}

// RBACOperationNames is the workspace operation catalog.
var RBACOperationNames = []string{"Read", "View", "Create", "Update", "Delete", "Download"}

// RBACPermissions returns the full cartesian catalog of resource x operation.
func RBACPermissions() []RBACPermission {
	perms := make([]RBACPermission, 0, len(RBACResourceNames)*len(RBACOperationNames))
	var id uint = 1
	for _, resource := range RBACResourceNames {
		for _, operation := range RBACOperationNames {
			perms = append(perms, RBACPermission{ID: id, Resource: resource, Operation: operation})
			id++
		}
	}
	return perms
}
