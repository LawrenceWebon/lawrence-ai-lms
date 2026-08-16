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
  "/health": ["get", "healthCheck"],
};

const expectedSchemas = [
  "AcceptInvitationRequest",
  "AuthenticationContextResponse",
  "AuthenticationMembershipResponse",
  "AuthenticationPrincipalResponse",
  "CreateInvitationRequest",
  "EntitlementResponse",
  "HealthResponse",
  "InvitationReceiptResponse",
  "MembershipSummaryResponse",
  "ProblemDetails",
  "TenantCandidateResponse",
  "TenantSummaryResponse",
  "UpdateMembershipRequest",
];

function requireF001Shape() {
  if (!String(schema.openapi).startsWith("3.1.")) {
    throw new Error("The generated client requires an OpenAPI 3.1 document.");
  }
  const actualPaths = Object.keys(schema.paths ?? {}).sort();
  const requiredPaths = Object.keys(expectedOperations).sort();
  if (JSON.stringify(actualPaths) !== JSON.stringify(requiredPaths)) {
    throw new Error("The OpenAPI paths no longer match the frozen F-001 integration contract.");
  }
  for (const [path, [method, operationId]] of Object.entries(expectedOperations)) {
    if (schema.paths[path]?.[method]?.operationId !== operationId) {
      throw new Error(`${path} no longer exposes ${operationId}.`);
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
  requireF001Shape();
  return `// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.
export type RoleCode = "tenant_admin" | "instructor" | "reviewer" | "learner";
export type MembershipStatus = "active" | "inactive";

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
