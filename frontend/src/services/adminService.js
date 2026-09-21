/**
 * adminService.js
 * ───────────────
 * Typed API service layer for the METRIX-LM Admin Command & Control Dashboard.
 * All calls are authenticated via the JWT Bearer token stored in localStorage.
 */

import api from './api';

// ─── User Management ──────────────────────────────────────────────────────────

export const fetchAllUsers = () => api.get('/admin/users');

export const createUser = (payload) =>
  api.post('/admin/users', payload);

export const updateUserRole = (userId, role) =>
  api.put(`/admin/users/${userId}/role`, { role });

// ─── Compliance Rule Engine ───────────────────────────────────────────────────

export const fetchAllRules = () => api.get('/admin/rules');

export const toggleRuleStatus = (ruleId, isActive, existingRule) =>
  api.post('/admin/rules', { ...existingRule, is_active: !isActive });

export const updateRuleParam = (ruleId, updatedRule) =>
  api.put(`/admin/rules/${ruleId}`, updatedRule);

/**
 * Bump rule engine version and hot-sync to the database.
 * @param {string} newVersion   - e.g. "v2.2"
 * @param {string} gsrnRef      - Optional Gazette reference number
 * @param {string} changelog    - Human-readable change summary
 * @param {string[]} ruleIds    - Specific rule IDs to update (empty = all)
 */
export const syncRuleVersion = (newVersion, gsrnRef, changelog, ruleIds = []) =>
  api.post('/admin/rules/update-version', {
    new_version: newVersion,
    gsrn_reference: gsrnRef || null,
    changelog: changelog || null,
    affected_rule_ids: ruleIds.length ? ruleIds : null,
  });

// ─── Work Assignment / Dispatch Engine ───────────────────────────────────────

/**
 * Assign an inspection to a specific user (inspector dispatch or officer review).
 * @param {string} inspectionId
 * @param {string} assignToUserId
 * @param {'inspector_dispatch'|'officer_review'} assignmentType
 * @param {string} notes
 */
export const assignWork = (inspectionId, assignToUserId, assignmentType, notes = '') =>
  api.post('/admin/assign-work', {
    inspection_id: inspectionId,
    assign_to_user_id: assignToUserId,
    assignment_type: assignmentType,
    notes,
  });

// ─── System Telemetry ─────────────────────────────────────────────────────────

export const fetchInspectionsSummary = () => api.get('/admin/inspections-summary');

export const fetchAuditLogs = (limit = 200) =>
  api.get(`/admin/audit-logs?limit=${limit}`);

export const clearSystemLogs = () =>
  api.post('/admin/clear-system-logs');

export const fetchInspections = () => api.get('/inspections');

