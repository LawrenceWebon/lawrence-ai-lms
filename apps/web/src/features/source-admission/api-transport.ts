import { createApiClient, type components } from "@ai-lms/api-client";

export type AuthenticationContext = components["schemas"]["AuthenticationContextResponse"];
export type CreateSourceAdmission = components["schemas"]["CreateSourceAdmissionV1"];
export type SourceAdmission = components["schemas"]["SourceAdmissionV1"];
export type SourceAdmissionStatus = SourceAdmission["source_version"]["admission_status"];
export type TenantCandidate = AuthenticationContext["available_tenants"][number];
export type UploadIntent = components["schemas"]["UploadIntentV1"];

export type SelectedTenant = {
  tenant: TenantCandidate;
  permissionCodes: string[];
};

type ProblemCode =
  | "AUTHENTICATION_REQUIRED"
  | "ACCESS_INACTIVE"
  | "RESOURCE_NOT_FOUND"
  | "RIGHTS_REQUIRED"
  | "SEPARATE_REVIEWER_REQUIRED"
  | "UPLOAD_EXPIRED"
  | "QUOTA_REACHED"
  | "VERSION_CONFLICT"
  | "REQUEST_INVALID"
  | "VALIDATION_UNAVAILABLE"
  | "TRANSPORT_UNAVAILABLE";

export class SourceAdmissionProblem extends Error {
  constructor(readonly code: ProblemCode) {
    super(code);
    this.name = "SourceAdmissionProblem";
  }
}

function remoteProblemCode(error: unknown): string | null {
  if (typeof error !== "object" || error === null || !("code" in error)) {
    return null;
  }
  return typeof error.code === "string" ? error.code : null;
}

function toProblem(error: unknown, status: number): SourceAdmissionProblem {
  const code = remoteProblemCode(error);
  if (status === 401 || code === "AUTHENTICATION_REQUIRED") {
    return new SourceAdmissionProblem("AUTHENTICATION_REQUIRED");
  }
  if (
    status === 403 ||
    code === "TENANT_ACCESS_INACTIVE" ||
    code === "SOURCE_PERMISSION_DENIED"
  ) {
    if (code === "SOURCE_RIGHTS_REVIEWER_SEPARATION_REQUIRED") {
      return new SourceAdmissionProblem("SEPARATE_REVIEWER_REQUIRED");
    }
    if (
      code === "SOURCE_RIGHTS_AUTHORIZATION_REQUIRED" ||
      code === "SOURCE_RIGHTS_AUTHORIZATION_DENIED"
    ) {
      return new SourceAdmissionProblem("RIGHTS_REQUIRED");
    }
    return new SourceAdmissionProblem("ACCESS_INACTIVE");
  }
  if (status === 404 || code === "RESOURCE_NOT_FOUND") {
    return new SourceAdmissionProblem("RESOURCE_NOT_FOUND");
  }
  if (status === 410 || code === "UPLOAD_INTENT_EXPIRED") {
    return new SourceAdmissionProblem("UPLOAD_EXPIRED");
  }
  if (status === 429 || code === "UPLOAD_QUOTA_EXCEEDED") {
    return new SourceAdmissionProblem("QUOTA_REACHED");
  }
  if (
    status === 409 ||
    code === "SOURCE_ADMISSION_STATE_CONFLICT" ||
    code === "SOURCE_ADMISSION_VERSION_CONFLICT" ||
    code === "IDEMPOTENCY_CONFLICT"
  ) {
    return new SourceAdmissionProblem("VERSION_CONFLICT");
  }
  if (status === 503 || code === "SOURCE_ADMISSION_VALIDATION_UNAVAILABLE") {
    return new SourceAdmissionProblem("VALIDATION_UNAVAILABLE");
  }
  if (status === 400 || status === 422 || code === "SOURCE_ADMISSION_VALIDATION_FAILED") {
    return new SourceAdmissionProblem("REQUEST_INVALID");
  }
  return new SourceAdmissionProblem("TRANSPORT_UNAVAILABLE");
}

function idempotencyKey(operation: string): string {
  return `${operation}-${crypto.randomUUID()}`;
}

export class ApiSourceAdmissionTransport {
  readonly #client = createApiClient("/f001-api");
  #accessToken: string | null = null;
  #tenantId: string | null = null;

  async signIn(credentials: { email: string; password: string }): Promise<TenantCandidate[]> {
    let response: Response;
    try {
      response = await fetch("/f001-api/api/integration/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
    } catch {
      throw new SourceAdmissionProblem("TRANSPORT_UNAVAILABLE");
    }
    if (!response.ok) {
      throw new SourceAdmissionProblem(
        response.status === 401 ? "AUTHENTICATION_REQUIRED" : "TRANSPORT_UNAVAILABLE",
      );
    }
    const payload: unknown = await response.json();
    if (
      typeof payload !== "object" ||
      payload === null ||
      !("access_token" in payload) ||
      typeof payload.access_token !== "string" ||
      payload.access_token.length < 32
    ) {
      throw new SourceAdmissionProblem("TRANSPORT_UNAVAILABLE");
    }
    this.#accessToken = payload.access_token;
    this.#tenantId = null;
    const context = await this.#authenticationContext(null);
    return context.available_tenants.filter(
      (tenant) => tenant.membership_status === "active",
    );
  }

  async selectTenant(tenantId: string, candidates: TenantCandidate[]): Promise<SelectedTenant> {
    if (!candidates.some((candidate) => candidate.id === tenantId)) {
      throw new SourceAdmissionProblem("RESOURCE_NOT_FOUND");
    }
    const context = await this.#authenticationContext(tenantId);
    const selected = context.available_tenants.find((tenant) => tenant.id === tenantId);
    if (
      context.active_tenant?.id !== tenantId ||
      selected?.membership_status !== "active" ||
      context.membership === null
    ) {
      throw new SourceAdmissionProblem("RESOURCE_NOT_FOUND");
    }
    this.#tenantId = tenantId;
    return { tenant: selected, permissionCodes: context.membership.permission_codes };
  }

  async createAdmission(command: CreateSourceAdmission): Promise<SourceAdmission> {
    const tenantId = this.#requireTenantId();
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/source-documents/admissions",
      {
        params: {
          path: { tenant_id: tenantId },
          header: this.#commandHeaders(idempotencyKey("create-source-admission")),
        },
        body: command,
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async review(
    snapshot: SourceAdmission,
    decision: "activate" | "deny" | "revoke",
  ): Promise<SourceAdmission> {
    const { tenantId, documentId, versionId } = this.#selectors(snapshot);
    const decisionCode = {
      activate: "RIGHTS_EVIDENCE_ACCEPTED",
      deny: "RIGHTS_EVIDENCE_INSUFFICIENT",
      revoke: "RIGHTS_REVOKED",
    } as const;
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/rights-authorizations/{authorization_id}/decisions",
      {
        params: {
          path: {
            tenant_id: tenantId,
            source_document_id: documentId,
            source_version_id: versionId,
            authorization_id: snapshot.store_authorization.id,
          },
          header: this.#commandHeaders(idempotencyKey(`source-rights-${decision}`)),
        },
        body: {
          decision,
          expected_authorization_row_version: snapshot.store_authorization.row_version,
          decision_code: decisionCode[decision],
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async createUploadIntent(snapshot: SourceAdmission): Promise<UploadIntent> {
    const { tenantId, documentId, versionId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/upload-intents",
      {
        params: {
          path: {
            tenant_id: tenantId,
            source_document_id: documentId,
            source_version_id: versionId,
          },
          header: this.#commandHeaders(idempotencyKey("source-upload-intent")),
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async upload(intent: UploadIntent, file: File): Promise<SourceAdmission> {
    const opaqueToken = intent.target_url.slice(intent.target_url.lastIndexOf("/") + 1);
    const { data, error, response } = await this.#client.PUT(
      "/api/v1/source-upload-targets/{opaque_token}",
      {
        params: { path: { opaque_token: opaqueToken } },
        headers: { "Content-Type": "application/pdf" },
        body: file,
        bodySerializer: (body) => body,
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async refresh(snapshot: SourceAdmission): Promise<SourceAdmission> {
    const { tenantId, documentId, versionId } = this.#selectors(snapshot);
    return this.getAdmission(documentId, versionId, tenantId);
  }

  async getAdmission(
    documentId: string,
    versionId: string,
    expectedTenantId?: string,
  ): Promise<SourceAdmission> {
    const tenantId = this.#requireTenantId();
    if (expectedTenantId !== undefined && expectedTenantId !== tenantId) {
      throw new SourceAdmissionProblem("RESOURCE_NOT_FOUND");
    }
    const { data, error, response } = await this.#client.GET(
      "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}",
      {
        params: {
          path: {
            tenant_id: tenantId,
            source_document_id: documentId,
            source_version_id: versionId,
          },
          header: this.#headers(),
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async cancel(snapshot: SourceAdmission): Promise<SourceAdmission> {
    const { tenantId, documentId, versionId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/cancel",
      {
        params: {
          path: {
            tenant_id: tenantId,
            source_document_id: documentId,
            source_version_id: versionId,
          },
          header: this.#commandHeaders(idempotencyKey("cancel-source-admission")),
        },
        body: {
          expected_source_version_row_version: snapshot.source_version.row_version,
          reason_code: "USER_CANCELLED",
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  signOut(): void {
    this.#accessToken = null;
    this.#tenantId = null;
  }

  async #authenticationContext(tenantId: string | null): Promise<AuthenticationContext> {
    const { data, error, response } = await this.#client.GET("/api/v1/auth-context", {
      params: {
        header: {
          Authorization: `Bearer ${this.#requireAccessToken()}`,
          ...(tenantId === null ? {} : { "X-Tenant-ID": tenantId }),
        },
      },
    });
    return this.#requireData(data, error, response.status);
  }

  #selectors(snapshot: SourceAdmission) {
    return {
      tenantId: this.#requireTenantId(),
      documentId: snapshot.source_document.id,
      versionId: snapshot.source_version.id,
    };
  }

  #headers() {
    return {
      Authorization: `Bearer ${this.#requireAccessToken()}`,
      "X-Tenant-ID": this.#requireTenantId(),
    };
  }

  #commandHeaders(key: string) {
    return { ...this.#headers(), "Idempotency-Key": key };
  }

  #requireAccessToken(): string {
    if (this.#accessToken === null) {
      throw new SourceAdmissionProblem("AUTHENTICATION_REQUIRED");
    }
    return this.#accessToken;
  }

  #requireTenantId(): string {
    if (this.#tenantId === null) {
      throw new SourceAdmissionProblem("RESOURCE_NOT_FOUND");
    }
    return this.#tenantId;
  }

  #requireData<T>(data: T | undefined, error: unknown, status: number): T {
    if (data === undefined) {
      throw toProblem(error, status);
    }
    return data;
  }
}
