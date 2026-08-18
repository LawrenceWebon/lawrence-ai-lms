import { createApiClient, type components } from "@ai-lms/api-client";

export type AuthenticationContext = components["schemas"]["AuthenticationContextResponse"];
export type CourseSnapshot = components["schemas"]["CourseSnapshotV1"];
export type CourseVersionHistory = components["schemas"]["CourseVersionHistoryV1"];
export type CourseStatus = CourseSnapshot["version"]["status"];
export type CurriculumSection = components["schemas"]["CurriculumSectionV1"];
export type TenantCandidate = AuthenticationContext["available_tenants"][number];

type ProblemCode =
  | "AUTHENTICATION_REQUIRED"
  | "ACCESS_INACTIVE"
  | "RESOURCE_NOT_FOUND"
  | "VERSION_CONFLICT"
  | "CONTENT_HASH_MISMATCH"
  | "COURSE_VERSION_IMMUTABLE"
  | "REQUEST_INVALID"
  | "TRANSPORT_UNAVAILABLE";

export class CourseEditorProblem extends Error {
  constructor(readonly code: ProblemCode) {
    super(code);
    this.name = "CourseEditorProblem";
  }
}

function remoteProblemCode(error: unknown): string | null {
  if (typeof error !== "object" || error === null || !("code" in error)) {
    return null;
  }
  return typeof error.code === "string" ? error.code : null;
}

function toProblem(error: unknown, status: number): CourseEditorProblem {
  const code = remoteProblemCode(error);
  if (status === 401 || code === "AUTHENTICATION_REQUIRED") {
    return new CourseEditorProblem("AUTHENTICATION_REQUIRED");
  }
  if (
    code === "TENANT_ACCESS_INACTIVE" ||
    code === "COURSE_PERMISSION_DENIED" ||
    status === 403
  ) {
    return new CourseEditorProblem("ACCESS_INACTIVE");
  }
  if (code === "RESOURCE_NOT_FOUND" || status === 404) {
    return new CourseEditorProblem("RESOURCE_NOT_FOUND");
  }
  if (code === "CONTENT_HASH_MISMATCH") {
    return new CourseEditorProblem("CONTENT_HASH_MISMATCH");
  }
  if (code === "COURSE_VERSION_IMMUTABLE") {
    return new CourseEditorProblem("COURSE_VERSION_IMMUTABLE");
  }
  if (code === "VERSION_CONFLICT" || code === "IDEMPOTENCY_CONFLICT" || status === 409) {
    return new CourseEditorProblem("VERSION_CONFLICT");
  }
  if (code === "COURSE_VALIDATION_FAILED" || status === 400 || status === 422) {
    return new CourseEditorProblem("REQUEST_INVALID");
  }
  return new CourseEditorProblem("TRANSPORT_UNAVAILABLE");
}

function idempotencyKey(operation: string): string {
  return `${operation}-${crypto.randomUUID()}`;
}

export class ApiCourseEditorTransport {
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
      throw new CourseEditorProblem("TRANSPORT_UNAVAILABLE");
    }
    if (!response.ok) {
      throw new CourseEditorProblem(
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
      throw new CourseEditorProblem("TRANSPORT_UNAVAILABLE");
    }
    this.#accessToken = payload.access_token;
    this.#tenantId = null;
    const context = await this.#authenticationContext(null);
    return context.available_tenants.filter(
      (tenant) => tenant.membership_status === "active",
    );
  }

  async selectTenant(tenantId: string, candidates: TenantCandidate[]): Promise<TenantCandidate> {
    if (!candidates.some((candidate) => candidate.id === tenantId)) {
      throw new CourseEditorProblem("RESOURCE_NOT_FOUND");
    }
    const context = await this.#authenticationContext(tenantId);
    const selected = context.available_tenants.find((tenant) => tenant.id === tenantId);
    if (context.active_tenant?.id !== tenantId || selected?.membership_status !== "active") {
      throw new CourseEditorProblem("RESOURCE_NOT_FOUND");
    }
    this.#tenantId = tenantId;
    return selected;
  }

  async createCourse(command: {
    slug: string;
    primary_locale: string;
    title: string;
    description: string;
  }): Promise<CourseSnapshot> {
    const tenantId = this.#requireTenantId();
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/courses",
      {
        params: {
          path: { tenant_id: tenantId },
          header: this.#commandHeaders(idempotencyKey("create-course")),
        },
        body: command,
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async updateDetails(
    snapshot: CourseSnapshot,
    command: { title: string; description: string },
  ): Promise<CourseSnapshot> {
    const { tenantId, courseId, versionId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.PATCH(
      "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}",
      {
        params: {
          path: { tenant_id: tenantId, course_id: courseId, version_id: versionId },
          header: this.#headers(),
        },
        body: {
          expected_version_row_version: snapshot.version.row_version,
          ...command,
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async replaceCurriculum(
    snapshot: CourseSnapshot,
    sections: CurriculumSection[],
  ): Promise<CourseSnapshot> {
    const { tenantId, courseId, versionId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.PUT(
      "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/curriculum",
      {
        params: {
          path: { tenant_id: tenantId, course_id: courseId, version_id: versionId },
          header: this.#headers(),
        },
        body: {
          expected_version_row_version: snapshot.version.row_version,
          sections,
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async transition(
    snapshot: CourseSnapshot,
    transition: "submit_review" | "request_changes" | "approve" | "publish" | "withdraw" | "archive",
  ): Promise<CourseSnapshot> {
    const { tenantId, courseId, versionId } = this.#selectors(snapshot);
    const params = {
      path: { tenant_id: tenantId, course_id: courseId, version_id: versionId },
      header: this.#commandHeaders(idempotencyKey(transition)),
    };
    const common = {
      expected_version_row_version: snapshot.version.row_version,
      expected_content_hash: snapshot.version.content_hash,
    };

    if (transition === "submit_review") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/submit-review",
        { params, body: { transition, ...common } },
      );
      return this.#requireData(data, error, response.status);
    }
    if (transition === "request_changes") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/request-changes",
        { params, body: { transition, ...common, reason_codes: ["NEEDS_REVISION"] } },
      );
      return this.#requireData(data, error, response.status);
    }
    if (transition === "approve") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/approve",
        { params, body: { transition, ...common } },
      );
      return this.#requireData(data, error, response.status);
    }
    if (transition === "publish") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish",
        {
          params,
          body: {
            transition,
            ...common,
            expected_course_row_version: snapshot.course.row_version,
          },
        },
      );
      return this.#requireData(data, error, response.status);
    }
    if (transition === "withdraw") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/withdraw",
        {
          params,
          body: {
            transition,
            ...common,
            expected_course_row_version: snapshot.course.row_version,
            reason_code: "SUPERSEDED",
          },
        },
      );
      return this.#requireData(data, error, response.status);
    }
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/archive",
      { params, body: { transition, ...common, reason_code: "SUPERSEDED" } },
    );
    return this.#requireData(data, error, response.status);
  }

  async createSuccessor(snapshot: CourseSnapshot): Promise<CourseSnapshot> {
    const { tenantId, courseId, versionId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/successor-draft",
      {
        params: {
          path: { tenant_id: tenantId, course_id: courseId, version_id: versionId },
          header: this.#commandHeaders(idempotencyKey("successor-draft")),
        },
        body: {
          expected_course_row_version: snapshot.course.row_version,
          expected_source_version_row_version: snapshot.version.row_version,
          expected_source_content_hash: snapshot.version.content_hash,
        },
      },
    );
    return this.#requireData(data, error, response.status).snapshot;
  }

  async history(snapshot: CourseSnapshot): Promise<CourseVersionHistory> {
    const { tenantId, courseId } = this.#selectors(snapshot);
    const { data, error, response } = await this.#client.GET(
      "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions",
      {
        params: {
          path: { tenant_id: tenantId, course_id: courseId },
          header: this.#headers(),
          query: { limit: 50 },
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
    const accessToken = this.#requireAccessToken();
    const { data, error, response } = await this.#client.GET("/api/v1/auth-context", {
      params: {
        header: {
          Authorization: `Bearer ${accessToken}`,
          ...(tenantId === null ? {} : { "X-Tenant-ID": tenantId }),
        },
      },
    });
    return this.#requireData(data, error, response.status);
  }

  #selectors(snapshot: CourseSnapshot) {
    return {
      tenantId: this.#requireTenantId(),
      courseId: snapshot.course.id,
      versionId: snapshot.version.id,
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
      throw new CourseEditorProblem("AUTHENTICATION_REQUIRED");
    }
    return this.#accessToken;
  }

  #requireTenantId(): string {
    if (this.#tenantId === null) {
      throw new CourseEditorProblem("RESOURCE_NOT_FOUND");
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
