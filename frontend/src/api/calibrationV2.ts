import type { Session } from "@supabase/supabase-js";
import { resolveApiBaseNormalized } from "../utils/apiBase";

const API_BASE = resolveApiBaseNormalized();

export type ReviewChoice = "A" | "B" | "tie" | "neither";

export interface CalibrationArtifact {
  artifact_id: string;
  artifact_type: string;
  url: string;
  duration_sec?: number | null;
  loudness_lufs?: number | null;
  sample_pack_version?: string | null;
}

export interface CandidateRatings {
  stylistic_authenticity: number;
  groove_feel: number;
  dynamics: number;
  phrasing: number;
  kit_balance: number;
  fill_behavior: number;
  human_realism: number;
  overall_usefulness: number;
}

export interface CalibrationReviewerItem {
  item_id: string;
  session_id: string;
  trial_id: string;
  target_drummer_slug: string;
  target_drummer_display_name: string;
  base_groove_id: string;
  eval_mode: "AB";
  lanes: {
    neutral: CalibrationArtifact[];
    A: CalibrationArtifact[];
    B: CalibrationArtifact[];
  };
  rubric: {
    choices: ReviewChoice[];
    rating_min: number;
    rating_max: number;
    minimum_listening_seconds_per_candidate: number;
  };
}

export interface ReviewerIdentity {
  reviewer_id: string;
  display_name: string;
  expertise_level?: string | null;
  consent_version?: string | null;
  is_active: boolean;
}

export interface ReviewerDrummer {
  drummer_slug: string;
  display_name: string;
  ready_trial_count: number;
}

export interface ReviewerSubmission {
  preferred_candidate: ReviewChoice;
  closer_to_target: ReviewChoice;
  better_feel: ReviewChoice;
  more_musical: ReviewChoice;
  confidence: number;
  technical_issue: boolean;
  cannot_judge: boolean;
  comment?: string;
  listening_ms: number;
  candidate_a_listening_ms: number;
  candidate_b_listening_ms: number;
  candidate_a_play_count: number;
  candidate_b_play_count: number;
  ratings_a?: CandidateRatings;
  ratings_b?: CandidateRatings;
}

interface ReviewResult {
  status: string;
  judgment_id: string;
  rating_ids: Record<string, string>;
  trial_id: string;
}

function accessToken(session: Session): string {
  const token = String(session.access_token || "").trim();
  if (!token) throw new Error("Reviewer session has no access token");
  return token;
}

async function apiRequest<T>(
  session: Session,
  path: string,
  init: RequestInit = {},
  idempotencyKey?: string,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken(session)}`,
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
      ...(init.headers || {}),
    },
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail || body?.message || `Calibration API returned HTTP ${response.status}`;
    throw new Error(String(detail));
  }
  return body as T;
}

export async function fetchReviewerIdentity(session: Session): Promise<ReviewerIdentity> {
  return apiRequest<ReviewerIdentity>(session, "/calibration/v2/reviewer/me");
}

export async function fetchReviewerDrummers(session: Session): Promise<ReviewerDrummer[]> {
  const response = await apiRequest<{ items: ReviewerDrummer[] }>(
    session,
    "/calibration/v2/reviewer/drummers",
  );
  return response.items || [];
}

export async function fetchNextReviewerItem(
  session: Session,
  targetDrummerSlug?: string,
): Promise<CalibrationReviewerItem | null> {
  const query = targetDrummerSlug
    ? `?target_drummer_slug=${encodeURIComponent(targetDrummerSlug)}`
    : "";
  const response = await apiRequest<{ item: CalibrationReviewerItem | null }>(
    session,
    `/calibration/v2/reviewer/next${query}`,
  );
  return response.item;
}

export async function submitReviewerItem(
  session: Session,
  itemId: string,
  payload: ReviewerSubmission,
  idempotencyKey: string,
): Promise<ReviewResult> {
  if (!idempotencyKey.trim()) throw new Error("Idempotency key is required");
  return apiRequest<ReviewResult>(
    session,
    `/calibration/v2/reviewer/items/${encodeURIComponent(itemId)}/review`,
    { method: "POST", body: JSON.stringify(payload) },
    idempotencyKey,
  );
}
