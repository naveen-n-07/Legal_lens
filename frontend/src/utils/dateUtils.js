/**
 * dateUtils.js — Centralized date parsing and relative-time formatting for METRIX-LM
 * Handles UTC strings, naive timestamps, and local timezone conversions gracefully.
 */

/**
 * Safely parses any server timestamp (UTC ISO, naive string, number, or Date)
 * into a valid JavaScript Date object in local time.
 */
export function parseServerDate(ts) {
  if (!ts) return null;
  if (ts instanceof Date) return isNaN(ts.getTime()) ? null : ts;
  if (typeof ts === 'number') return new Date(ts);

  if (typeof ts === 'string') {
    let clean = ts.trim().replace(' ', 'T');
    // If string has no timezone indicator (no 'Z' and no offset like +05:30 or -04:00)
    // append 'Z' because the server timestamp is generated in UTC.
    if (!clean.endsWith('Z') && !/[+-]\d{2}(:?\d{2})?$/.test(clean)) {
      clean += 'Z';
    }
    const d = new Date(clean);
    if (!isNaN(d.getTime())) return d;
  }

  const fallback = new Date(ts);
  return isNaN(fallback.getTime()) ? null : fallback;
}

/**
 * Formats a timestamp for display in Indian Standard / User locale.
 * Example output: "21 Sept, 04:51 pm" or "21 Sept 2026, 04:51 pm"
 */
export function formatDateTime(ts, options = {}) {
  const d = parseServerDate(ts);
  if (!d) return '—';

  const defaultOpts = {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    ...options
  };

  return d.toLocaleString('en-IN', defaultOpts);
}

/**
 * Formats date only, e.g. "21 Sept 2026"
 */
export function formatDateOnly(ts) {
  const d = parseServerDate(ts);
  if (!d) return '—';
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

/**
 * Calculates live elapsed wait time from a submission timestamp.
 * Returns { text: "2m wait", hours: 0, minutes: 2, isUrgent: false }
 */
export function getElapsedWaitTime(ts) {
  const d = parseServerDate(ts);
  if (!d) return { text: '< 1m wait', hours: 0, isUrgent: false };

  const now = Date.now();
  const created = d.getTime();
  const diffMs = Math.max(0, now - created);
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  let text = '';
  if (diffDays > 0) {
    const remHours = diffHours % 24;
    text = `${diffDays}d ${remHours}h wait`;
  } else if (diffHours > 0) {
    const remMins = diffMins % 60;
    text = `${diffHours}h ${remMins}m wait`;
  } else if (diffMins > 0) {
    text = `${diffMins}m wait`;
  } else {
    text = '< 1m wait';
  }

  return {
    text,
    hours: diffHours,
    minutes: diffMins,
    isUrgent: diffHours >= 24
  };
}

/**
 * Calculates relative time string (e.g. "just now", "5m ago", "2h ago", "1d ago")
 */
export function getRelativeTime(ts) {
  const d = parseServerDate(ts);
  if (!d) return '—';

  const diffMs = Date.now() - d.getTime();
  const m = Math.floor(diffMs / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const days = Math.floor(h / 24);
  return `${days}d ago`;
}
