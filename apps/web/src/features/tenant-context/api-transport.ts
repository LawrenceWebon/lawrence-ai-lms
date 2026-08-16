import { createApiClient, type components } from "@ai-lms/api-client";

import {
  type ActiveTenant,
  TenantContextProblem,
  type TenantCandidate,
  type TenantContextTransport,
  type TransportProblemCode,
} from "./transport";

type AuthenticationContext = components["schemas"]["AuthenticationContextResponse"];

function problemCode(error: unknown, status: number): TransportProblemCode {
  if (typeof error === "object" && error !== null && "code" in error) {
    const code = String(error.code);
    if (
      code === "AUTHENTICATION_REQUIRED" ||
      code === "INVITATION_INVALID" ||
      code === "TENANT_ACCESS_DENIED" ||
      code === "TENANT_ACCESS_INACTIVE"
    ) {
      return code;
    }
  }
  if (status === 401) {
    return "AUTHENTICATION_REQUIRED";
  }
  return "TRANSPORT_UNAVAILABLE";
}

function candidates(context: AuthenticationContext): TenantCandidate[] {
  return context.available_tenants
    .filter((tenant) => tenant.membership_status === "active")
    .map((tenant) => ({
      id: tenant.id,
      slug: tenant.slug,
      displayName: tenant.display_name,
      membershipStatus: "active",
    }));
}

export class ApiTenantContextTransport implements TenantContextTransport {
  readonly #client = createApiClient("/f001-api");
  #accessToken: string | null = null;
  #activeTenantId: string | null = null;

  async signIn(credentials: { email: string; password: string }): Promise<TenantCandidate[]> {
    let response: Response;
    try {
      response = await fetch("/f001-api/api/integration/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
    } catch {
      throw new TenantContextProblem("TRANSPORT_UNAVAILABLE");
    }
    if (!response.ok) {
      throw new TenantContextProblem(
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
      throw new TenantContextProblem("TRANSPORT_UNAVAILABLE");
    }
    this.#accessToken = payload.access_token;
    this.#activeTenantId = null;
    return candidates(await this.#loadContext(null));
  }

  async selectTenant(selector: string, available: TenantCandidate[]): Promise<ActiveTenant> {
    if (!available.some((tenant) => tenant.id === selector)) {
      throw new TenantContextProblem("TENANT_ACCESS_DENIED");
    }
    const context = await this.#loadContext(selector);
    if (context.active_tenant?.id !== selector) {
      throw new TenantContextProblem("TENANT_ACCESS_DENIED");
    }
    this.#activeTenantId = selector;
    return {
      id: context.active_tenant.id,
      slug: context.active_tenant.slug,
      displayName: context.active_tenant.display_name,
    };
  }

  async acceptInvitation(token: string): Promise<"accepted"> {
    const accessToken = this.#requireAccessToken();
    const { data, error, response } = await this.#client.POST(
      "/api/v1/tenant-invitations/accept",
      {
        params: { header: { Authorization: `Bearer ${accessToken}` } },
        body: { invitation_token: token },
      },
    );
    if (!data) {
      throw new TenantContextProblem(problemCode(error, response.status));
    }
    return "accepted";
  }

  async refreshAccess(available: TenantCandidate[]): Promise<TenantCandidate[]> {
    void available;
    return candidates(await this.#loadContext(this.#activeTenantId));
  }

  signOut(): void {
    this.#accessToken = null;
    this.#activeTenantId = null;
  }

  async #loadContext(tenantId: string | null): Promise<AuthenticationContext> {
    const accessToken = this.#requireAccessToken();
    const { data, error, response } = await this.#client.GET("/api/v1/auth-context", {
      params: {
        header: {
          Authorization: `Bearer ${accessToken}`,
          ...(tenantId === null ? {} : { "X-Tenant-ID": tenantId }),
        },
      },
    });
    if (!data) {
      throw new TenantContextProblem(problemCode(error, response.status));
    }
    return data;
  }

  #requireAccessToken(): string {
    if (this.#accessToken === null) {
      throw new TenantContextProblem("AUTHENTICATION_REQUIRED");
    }
    return this.#accessToken;
  }
}
