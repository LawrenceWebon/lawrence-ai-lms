import { createApiClient, type components } from "@ai-lms/api-client";

export type AuthenticationContext = components["schemas"]["AuthenticationContextResponse"];
export type DashboardCard = components["schemas"]["DashboardCardV1"];
export type LearnerDashboard = components["schemas"]["LearnerDashboardV1"];
export type LessonPlayback = components["schemas"]["LessonPlaybackV1"];
export type PlaybackSnapshot = components["schemas"]["PlaybackSnapshotV1"];
export type ProgressCommandName = components["schemas"]["ProgressCommandV1"]["command"];
export type ProgressResult = components["schemas"]["ProgressResultV1"];
export type TenantCandidate = AuthenticationContext["available_tenants"][number];

type ProblemCode =
  | "AUTHENTICATION_REQUIRED"
  | "ACCESS_INACTIVE"
  | "RESOURCE_NOT_FOUND"
  | "VERSION_CONFLICT"
  | "REQUEST_INVALID"
  | "TRANSPORT_UNAVAILABLE";

export class LearnerPlaybackProblem extends Error {
  constructor(readonly code: ProblemCode) {
    super(code);
    this.name = "LearnerPlaybackProblem";
  }
}

function remoteProblemCode(error: unknown): string | null {
  if (typeof error !== "object" || error === null || !("code" in error)) {
    return null;
  }
  return typeof error.code === "string" ? error.code : null;
}

function toProblem(error: unknown, status: number): LearnerPlaybackProblem {
  const code = remoteProblemCode(error);
  if (status === 401 || code === "AUTHENTICATION_REQUIRED") {
    return new LearnerPlaybackProblem("AUTHENTICATION_REQUIRED");
  }
  if (status === 403 || code === "TENANT_ACCESS_INACTIVE") {
    return new LearnerPlaybackProblem("ACCESS_INACTIVE");
  }
  if (status === 404 || code === "LEARNING_RESOURCE_NOT_FOUND") {
    return new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
  }
  if (
    status === 409 ||
    code === "PROGRESS_VERSION_CONFLICT" ||
    code === "IDEMPOTENCY_CONFLICT"
  ) {
    return new LearnerPlaybackProblem("VERSION_CONFLICT");
  }
  if (status === 400 || status === 422 || code === "ENROLLMENT_VALIDATION_FAILED") {
    return new LearnerPlaybackProblem("REQUEST_INVALID");
  }
  return new LearnerPlaybackProblem("TRANSPORT_UNAVAILABLE");
}

function idempotencyKey(operation: string): string {
  return `${operation}-${crypto.randomUUID()}`;
}

export class ApiLearnerPlaybackTransport {
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
      throw new LearnerPlaybackProblem("TRANSPORT_UNAVAILABLE");
    }
    if (!response.ok) {
      throw new LearnerPlaybackProblem(
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
      throw new LearnerPlaybackProblem("TRANSPORT_UNAVAILABLE");
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
      throw new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
    }
    const context = await this.#authenticationContext(tenantId);
    const selected = context.available_tenants.find((tenant) => tenant.id === tenantId);
    if (context.active_tenant?.id !== tenantId || selected?.membership_status !== "active") {
      throw new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
    }
    this.#tenantId = tenantId;
    return selected;
  }

  async dashboard(cursor?: string): Promise<LearnerDashboard> {
    const tenantId = this.#requireTenantId();
    const { data, error, response } = await this.#client.GET(
      "/api/v1/tenants/{tenant_id}/learner/courses",
      {
        params: {
          path: { tenant_id: tenantId },
          header: this.#headers(),
          query: { limit: 50, ...(cursor === undefined ? {} : { cursor }) },
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async playback(enrollmentId: string): Promise<PlaybackSnapshot> {
    const tenantId = this.#requireTenantId();
    const { data, error, response } = await this.#client.GET(
      "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/playback",
      {
        params: {
          path: { tenant_id: tenantId, enrollment_id: enrollmentId },
          header: this.#headers(),
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async lesson(enrollmentId: string, lessonId: string): Promise<LessonPlayback> {
    const tenantId = this.#requireTenantId();
    const { data, error, response } = await this.#client.GET(
      "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/lessons/{lesson_id}",
      {
        params: {
          path: {
            tenant_id: tenantId,
            enrollment_id: enrollmentId,
            lesson_id: lessonId,
          },
          header: this.#headers(),
        },
      },
    );
    return this.#requireData(data, error, response.status);
  }

  async progress(
    enrollmentId: string,
    lessonId: string,
    command: ProgressCommandName,
    expectedProgressRowVersion: number,
  ): Promise<ProgressResult> {
    const tenantId = this.#requireTenantId();
    const params = {
      path: { tenant_id: tenantId, enrollment_id: enrollmentId },
      header: {
        ...this.#headers(),
        "Idempotency-Key": idempotencyKey(command),
      },
    };
    const body = {
      command,
      lesson_id: lessonId,
      expected_progress_row_version: expectedProgressRowVersion,
    };
    if (command === "open_lesson") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/open-lesson",
        { params, body },
      );
      return this.#requireData(data, error, response.status);
    }
    if (command === "complete_lesson") {
      const { data, error, response } = await this.#client.POST(
        "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/complete-lesson",
        { params, body },
      );
      return this.#requireData(data, error, response.status);
    }
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/reopen-lesson",
      { params, body },
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

  #headers() {
    return {
      Authorization: `Bearer ${this.#requireAccessToken()}`,
      "X-Tenant-ID": this.#requireTenantId(),
    };
  }

  #requireAccessToken(): string {
    if (this.#accessToken === null) {
      throw new LearnerPlaybackProblem("AUTHENTICATION_REQUIRED");
    }
    return this.#accessToken;
  }

  #requireTenantId(): string {
    if (this.#tenantId === null) {
      throw new LearnerPlaybackProblem("RESOURCE_NOT_FOUND");
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
