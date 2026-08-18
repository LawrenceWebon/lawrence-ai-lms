#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";

const sourcePath = "contracts/openapi/openapi.json";
const outputPath = "packages/api-client/src/generated/schema.d.ts";
const schema = JSON.parse(readFileSync(sourcePath, "utf8"));

const expectedOperations = {
  "/api/v1/auth-context": ["get", "getAuthenticationContext"],
  "/api/v1/tenant-invitations/accept": ["post", "acceptTenantInvitation"],
  "/api/v1/tenants/{tenant_id}/invitations": ["post", "createTenantInvitation"],
  "/api/v1/tenants/{tenant_id}/memberships": ["get", "listTenantMemberships"],
  "/api/v1/tenants/{tenant_id}/memberships/{membership_id}": [
    "patch",
    "updateTenantMembership",
  ],
  "/api/v1/tenants/{tenant_id}/courses": ["post", "createCourse"],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions": [
    "get",
    "listCourseVersions",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}": [
    "get",
    "getCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}#patch": [
    "patch",
    "updateCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/curriculum": [
    "put",
    "replaceCourseCurriculum",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/submit-review": [
    "post",
    "submitCourseReview",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/request-changes": [
    "post",
    "requestCourseChanges",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/approve": [
    "post",
    "approveCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish": [
    "post",
    "publishCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/withdraw": [
    "post",
    "withdrawCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/archive": [
    "post",
    "archiveCourseVersion",
  ],
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/successor-draft": [
    "post",
    "createSuccessorCourseDraft",
  ],
  "/health": ["get", "healthCheck"],
};

const expectedSchemas = [
  "AcceptInvitationRequest",
  "AuthenticationContextResponse",
  "AuthenticationMembershipResponse",
  "AuthenticationPrincipalResponse",
  "CreateInvitationRequest",
  "CreateCourseV1",
  "CreateSuccessorDraftV1",
  "CourseSnapshotV1",
  "CourseVersionHistoryV1",
  "ReplaceCurriculumV1",
  "SuccessorDraftResultV1",
  "TransitionCourseVersionV1",
  "UpdateCourseVersionV1",
  "EntitlementResponse",
  "HealthResponse",
  "InvitationReceiptResponse",
  "MembershipSummaryResponse",
  "ProblemDetails",
  "TenantCandidateResponse",
  "TenantSummaryResponse",
  "UpdateMembershipRequest",
];

function requireIntegratedShape() {
  if (!String(schema.openapi).startsWith("3.1.")) {
    throw new Error("The generated client requires an OpenAPI 3.1 document.");
  }
  const operationEntries = Object.entries(expectedOperations);
  const actualPaths = Object.keys(schema.paths ?? {}).sort();
  const requiredPaths = [...new Set(operationEntries.map(([path]) => path.split("#")[0]))].sort();
  if (JSON.stringify(actualPaths) !== JSON.stringify(requiredPaths)) {
    throw new Error("The OpenAPI paths no longer match the frozen integrated API contract.");
  }
  for (const [contractPath, [method, operationId]] of operationEntries) {
    const path = contractPath.split("#")[0];
    if (schema.paths[path]?.[method]?.operationId !== operationId) {
      throw new Error(`${path} ${method} no longer exposes ${operationId}.`);
    }
  }
  const components = schema.components?.schemas ?? {};
  for (const name of expectedSchemas) {
    if (components[name] === undefined) {
      throw new Error(`OpenAPI component ${name} is missing.`);
    }
  }
}

function render() {
  requireIntegratedShape();
  return `// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.
export type RoleCode = "tenant_admin" | "instructor" | "reviewer" | "learner";
export type MembershipStatus = "active" | "inactive";
export type CourseStatus =
  | "draft"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "scheduled"
  | "published"
  | "withdrawn"
  | "archived";
export type CourseOrigin = "manual" | "ai_assisted";
export type ReviewerPolicy = "self_review_allowed" | "separate_reviewer_required";
export type ReviewDecision = "changes_requested" | "approved";
export type TransitionName =
  | "submit_review"
  | "request_changes"
  | "approve"
  | "publish"
  | "withdraw"
  | "archive";
export type RichTextMark = "strong" | "emphasis" | "code";

export interface paths {
  "/health": {
    parameters: EmptyParameters;
    get: operations["healthCheck"];
  };
  "/api/v1/auth-context": {
    parameters: EmptyParameters;
    get: operations["getAuthenticationContext"];
  };
  "/api/v1/tenant-invitations/accept": {
    parameters: EmptyParameters;
    post: operations["acceptTenantInvitation"];
  };
  "/api/v1/tenants/{tenant_id}/invitations": {
    parameters: EmptyParameters;
    post: operations["createTenantInvitation"];
  };
  "/api/v1/tenants/{tenant_id}/memberships": {
    parameters: EmptyParameters;
    get: operations["listTenantMemberships"];
  };
  "/api/v1/tenants/{tenant_id}/memberships/{membership_id}": {
    parameters: EmptyParameters;
    patch: operations["updateTenantMembership"];
  };
  "/api/v1/tenants/{tenant_id}/courses": {
    parameters: EmptyParameters;
    post: operations["createCourse"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions": {
    parameters: EmptyParameters;
    get: operations["listCourseVersions"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}": {
    parameters: EmptyParameters;
    get: operations["getCourseVersion"];
    patch: operations["updateCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/curriculum": {
    parameters: EmptyParameters;
    put: operations["replaceCourseCurriculum"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/submit-review": {
    parameters: EmptyParameters;
    post: operations["submitCourseReview"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/request-changes": {
    parameters: EmptyParameters;
    post: operations["requestCourseChanges"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/approve": {
    parameters: EmptyParameters;
    post: operations["approveCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish": {
    parameters: EmptyParameters;
    post: operations["publishCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/withdraw": {
    parameters: EmptyParameters;
    post: operations["withdrawCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/archive": {
    parameters: EmptyParameters;
    post: operations["archiveCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/successor-draft": {
    parameters: EmptyParameters;
    post: operations["createSuccessorCourseDraft"];
  };
}

export interface components {
  schemas: {
    AcceptInvitationRequest: {
      invitation_token: string;
    };
    AuthenticationContextResponse: {
      "$schema": "https://contracts.ai-lms.local/f001/auth-context.v1.schema.json";
      principal: components["schemas"]["AuthenticationPrincipalResponse"];
      active_tenant: components["schemas"]["TenantSummaryResponse"] | null;
      membership: components["schemas"]["AuthenticationMembershipResponse"] | null;
      entitlement: components["schemas"]["EntitlementResponse"] | null;
      available_tenants: components["schemas"]["TenantCandidateResponse"][];
    };
    AuthenticationMembershipResponse: {
      id: string;
      status: MembershipStatus;
      row_version: number;
      role_codes: string[];
      permission_codes: string[];
    };
    AuthenticationPrincipalResponse: {
      user_id: string;
      authentication_time: string;
      assurance_level: "aal1" | "aal2";
    };
    CreateInvitationRequest: {
      email: string;
      role_codes: RoleCode[];
    };
    EntitlementResponse: {
      status: "active" | "expired" | "suspended";
      valid_until: string | null;
    };
    HealthResponse: {
      capabilities: string[];
      service: string;
      status: string;
    };
    InvitationReceiptResponse: {
      id: string;
      tenant_id: string;
      status: string;
      expires_at: string;
    };
    MembershipSummaryResponse: {
      id: string;
      tenant_id: string;
      status: string;
      row_version: number;
      role_codes: RoleCode[];
    };
    ProblemDetails: {
      type: string;
      title: string;
      status: number;
      detail: string;
      code: string;
      request_id: string;
      errors: Record<string, unknown>[];
    };
    TenantCandidateResponse: components["schemas"]["TenantSummaryResponse"] & {
      membership_status: MembershipStatus;
    };
    TenantSummaryResponse: {
      id: string;
      slug: string;
      display_name: string;
    };
    UpdateMembershipRequest: {
      status?: MembershipStatus | null;
      role_codes?: RoleCode[] | null;
      row_version: number;
    };
    TextNode: {
      type: "text";
      text: string;
      marks: RichTextMark[];
    };
    ParagraphNode: {
      type: "paragraph";
      content: components["schemas"]["TextNode"][];
    };
    HeadingNode: {
      type: "heading";
      level: 2 | 3 | 4;
      content: components["schemas"]["TextNode"][];
    };
    ListItemNode: {
      type: "list_item";
      content: components["schemas"]["ParagraphNode"][];
    };
    BulletListNode: {
      type: "bullet_list";
      items: components["schemas"]["ListItemNode"][];
    };
    OrderedListNode: {
      type: "ordered_list";
      items: components["schemas"]["ListItemNode"][];
    };
    RichTextDocument: {
      type: "document";
      content: Array<
        | components["schemas"]["ParagraphNode"]
        | components["schemas"]["HeadingNode"]
        | components["schemas"]["BulletListNode"]
        | components["schemas"]["OrderedListNode"]
      >;
    };
    CurriculumBlockV1: {
      id?: string;
      expected_row_version?: number;
      kind: "rich_text";
      position: number;
      document: components["schemas"]["RichTextDocument"];
    };
    CurriculumLessonV1: {
      id?: string;
      expected_row_version?: number;
      title: string;
      position: number;
      is_required: boolean;
      content_blocks: components["schemas"]["CurriculumBlockV1"][];
    };
    CurriculumSectionV1: {
      id?: string;
      expected_row_version?: number;
      title: string;
      position: number;
      lessons: components["schemas"]["CurriculumLessonV1"][];
    };
    CreateCourseV1: {
      slug: string;
      primary_locale: string;
      title: string;
      description: string;
    };
    UpdateCourseVersionV1: {
      expected_version_row_version: number;
      primary_locale?: string;
      title?: string;
      description?: string;
    };
    ReplaceCurriculumV1: {
      expected_version_row_version: number;
      sections: components["schemas"]["CurriculumSectionV1"][];
    };
    TransitionCourseVersionV1: {
      transition: TransitionName;
      expected_version_row_version: number;
      expected_course_row_version?: number;
      expected_content_hash: string;
      reason_code?: string;
      reason_codes?: string[];
    };
    CreateSuccessorDraftV1: {
      expected_course_row_version: number;
      expected_source_version_row_version: number;
      expected_source_content_hash: string;
    };
    CourseRecordV1: {
      id: string;
      tenant_id: string;
      slug: string;
      reviewer_policy: ReviewerPolicy;
      current_published_version_id: string | null;
      instructor_membership_ids: string[];
      row_version: number;
    };
    CourseVersionRecordV1: {
      id: string;
      tenant_id: string;
      course_id: string;
      predecessor_version_id: string | null;
      version_number: number;
      status: CourseStatus;
      origin_type: CourseOrigin;
      primary_locale: string;
      title: string;
      description: string;
      content_hash: string;
      submitted_hash: string | null;
      approved_hash: string | null;
      row_version: number;
    };
    ContentBlockRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      lesson_id: string;
      kind: "rich_text";
      position: number;
      row_version: number;
      document: components["schemas"]["RichTextDocument"];
    };
    LessonRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      section_id: string;
      title: string;
      position: number;
      is_required: boolean;
      row_version: number;
      content_blocks: components["schemas"]["ContentBlockRecordV1"][];
    };
    SectionRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      title: string;
      position: number;
      row_version: number;
      lessons: components["schemas"]["LessonRecordV1"][];
    };
    CourseReviewV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      decision: ReviewDecision;
      reviewed_hash: string;
      reviewer_id: string;
      self_review: boolean;
      reason_codes: string[];
      decided_at: string;
    };
    CourseSnapshotV1: {
      "$schema": "https://contracts.ai-lms.local/f002/canonical-course.v1.schema.json";
      course: components["schemas"]["CourseRecordV1"];
      version: components["schemas"]["CourseVersionRecordV1"];
      sections: components["schemas"]["SectionRecordV1"][];
      latest_review: components["schemas"]["CourseReviewV1"] | null;
    };
    CourseVersionSummaryV1: {
      id: string;
      tenant_id: string;
      course_id: string;
      predecessor_version_id: string | null;
      version_number: number;
      status: CourseStatus;
      title: string;
      content_hash: string;
      row_version: number;
      is_current_published: boolean;
    };
    CourseVersionHistoryV1: {
      tenant_id: string;
      course_id: string;
      current_published_version_id: string | null;
      versions: components["schemas"]["CourseVersionSummaryV1"][];
      next_cursor: string | null;
    };
    SuccessorDraftResultV1: {
      source_version_id: string;
      successor_version_id: string;
      snapshot: components["schemas"]["CourseSnapshotV1"];
    };
  };
}

export interface operations {
  healthCheck: {
    parameters: EmptyParameters;
    requestBody?: never;
    responses: { 200: JsonResponse<components["schemas"]["HealthResponse"]> };
  };
  getAuthenticationContext: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["AuthenticationContextResponse"]>;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  acceptTenantInvitation: {
    parameters: AuthParameters;
    requestBody: JsonRequest<components["schemas"]["AcceptInvitationRequest"]>;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"]>;
      401: ProblemResponse;
      404: ProblemResponse;
      410: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  createTenantInvitation: {
    parameters: {
      query?: never;
      header: AuthHeaders & { "Idempotency-Key": string; "X-Tenant-ID"?: string | null };
      path: { tenant_id: string };
      cookie?: never;
    };
    requestBody: JsonRequest<components["schemas"]["CreateInvitationRequest"]>;
    responses: {
      201: JsonResponse<components["schemas"]["InvitationReceiptResponse"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  listTenantMemberships: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path: { tenant_id: string };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"][]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  updateTenantMembership: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path: { tenant_id: string; membership_id: string };
      cookie?: never;
    };
    requestBody: JsonRequest<components["schemas"]["UpdateMembershipRequest"]>;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  createCourse: {
    parameters: CourseCollectionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateCourseV1"]>;
    responses: {
      201: JsonResponse<components["schemas"]["CourseSnapshotV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getCourseVersion: {
    parameters: CourseVersionParameters;
    requestBody?: never;
    responses: CourseSnapshotResponses;
  };
  listCourseVersions: {
    parameters: CourseHistoryParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["CourseVersionHistoryV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  updateCourseVersion: {
    parameters: CourseVersionParameters;
    requestBody: JsonRequest<components["schemas"]["UpdateCourseVersionV1"]>;
    responses: CourseSnapshotResponses;
  };
  replaceCourseCurriculum: {
    parameters: CourseVersionParameters;
    requestBody: JsonRequest<components["schemas"]["ReplaceCurriculumV1"]>;
    responses: CourseSnapshotResponses;
  };
  submitCourseReview: CourseTransitionOperation;
  requestCourseChanges: CourseTransitionOperation;
  approveCourseVersion: CourseTransitionOperation;
  publishCourseVersion: CourseTransitionOperation;
  withdrawCourseVersion: CourseTransitionOperation;
  archiveCourseVersion: CourseTransitionOperation;
  createSuccessorCourseDraft: {
    parameters: CourseVersionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateSuccessorDraftV1"]>;
    responses: {
      200: JsonResponse<components["schemas"]["SuccessorDraftResultV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
}

type EmptyParameters = {
  query?: never;
  header?: never;
  path?: never;
  cookie?: never;
};
type AuthHeaders = { Authorization?: string | null };
type AuthParameters = {
  query?: never;
  header?: AuthHeaders;
  path?: never;
  cookie?: never;
};
type CourseHeaders = AuthHeaders & { "X-Tenant-ID": string };
type CourseCollectionCommandParameters = {
  query?: never;
  header: CourseHeaders & { "Idempotency-Key": string };
  path: { tenant_id: string };
  cookie?: never;
};
type CourseVersionParameters = {
  query?: never;
  header: CourseHeaders;
  path: { tenant_id: string; course_id: string; version_id: string };
  cookie?: never;
};
type CourseVersionCommandParameters = Omit<CourseVersionParameters, "header"> & {
  header: CourseHeaders & { "Idempotency-Key": string };
};
type CourseHistoryParameters = {
  query?: { cursor?: string | null; limit?: number };
  header: CourseHeaders;
  path: { tenant_id: string; course_id: string };
  cookie?: never;
};
type CourseSnapshotResponses = {
  200: JsonResponse<components["schemas"]["CourseSnapshotV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type CourseTransitionOperation = {
  parameters: CourseVersionCommandParameters;
  requestBody: JsonRequest<components["schemas"]["TransitionCourseVersionV1"]>;
  responses: CourseSnapshotResponses;
};
type JsonRequest<T> = { content: { "application/json": T } };
type JsonResponse<T> = {
  headers: Record<string, unknown>;
  content: { "application/json": T };
};
type ProblemResponse = {
  headers: Record<string, unknown>;
  content: {
    "application/json": components["schemas"]["ProblemDetails"];
    "application/problem+json": components["schemas"]["ProblemDetails"];
  };
};
`;
}

const expected = render();
if (process.argv.includes("--check")) {
  const current = readFileSync(outputPath, "utf8");
  if (current !== expected) {
    throw new Error(`Generated client drift detected; run node ${process.argv[1]}`);
  }
  console.log("Generated TypeScript API schema is current.");
} else {
  writeFileSync(outputPath, expected, "utf8");
  console.log(`Generated ${outputPath}`);
}
