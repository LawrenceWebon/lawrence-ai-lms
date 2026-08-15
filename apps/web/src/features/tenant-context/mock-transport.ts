export type TenantCandidate = {
  id: string;
  slug: string;
  displayName: string;
  membershipStatus: "active";
};

export type ActiveTenant = Pick<TenantCandidate, "id" | "slug" | "displayName">;

export type MockScenario =
  | "auth-error"
  | "denied"
  | "empty"
  | "error"
  | "multi"
  | "session-expired"
  | "single";

export type TransportProblemCode =
  | "AUTHENTICATION_REQUIRED"
  | "INVITATION_INVALID"
  | "TENANT_ACCESS_DENIED"
  | "TRANSPORT_UNAVAILABLE";

export class MockTransportProblem extends Error {
  constructor(readonly code: TransportProblemCode) {
    super(code);
    this.name = "MockTransportProblem";
  }
}

const alpha: TenantCandidate = {
  id: "00000000-0000-4000-8000-0000000000a1",
  slug: "alpha",
  displayName: "Alpha Learning",
  membershipStatus: "active",
};

const beta: TenantCandidate = {
  id: "00000000-0000-4000-8000-0000000000b1",
  slug: "beta",
  displayName: "Beta Learning",
  membershipStatus: "active",
};

const activeInvitation = "synthetic-active-token-000000000001";

function normalizeScenario(value: string | undefined): MockScenario {
  switch (value) {
    case "auth-error":
    case "denied":
    case "empty":
    case "error":
    case "session-expired":
    case "single":
      return value;
    default:
      return "multi";
  }
}

async function waitForFixture(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 120));
}

export class MockTenantContextTransport {
  readonly #acceptedInvitations = new Set<string>();
  readonly #scenario: MockScenario;

  constructor(scenario: string | undefined) {
    this.#scenario = normalizeScenario(scenario);
  }

  async signIn(credentials: { email: string; password: string }): Promise<TenantCandidate[]> {
    await waitForFixture();

    if (!credentials.email || !credentials.password || this.#scenario === "auth-error") {
      throw new MockTransportProblem("AUTHENTICATION_REQUIRED");
    }
    if (this.#scenario === "error") {
      throw new MockTransportProblem("TRANSPORT_UNAVAILABLE");
    }
    if (this.#scenario === "empty") {
      return [];
    }
    if (this.#scenario === "single") {
      return [alpha];
    }
    return [alpha, beta];
  }

  async selectTenant(selector: string, candidates: TenantCandidate[]): Promise<ActiveTenant> {
    await waitForFixture();
    const candidate = candidates.find((tenant) => tenant.id === selector);

    if (!candidate || this.#scenario === "denied") {
      throw new MockTransportProblem("TENANT_ACCESS_DENIED");
    }

    return { id: candidate.id, slug: candidate.slug, displayName: candidate.displayName };
  }

  async acceptInvitation(token: string): Promise<"accepted" | "already-accepted"> {
    await waitForFixture();

    if (token !== activeInvitation) {
      throw new MockTransportProblem("INVITATION_INVALID");
    }
    if (this.#acceptedInvitations.has(token)) {
      return "already-accepted";
    }

    this.#acceptedInvitations.add(token);
    return "accepted";
  }

  async refreshAccess(candidates: TenantCandidate[]): Promise<TenantCandidate[]> {
    await waitForFixture();
    if (this.#scenario === "session-expired") {
      throw new MockTransportProblem("AUTHENTICATION_REQUIRED");
    }
    return candidates;
  }
}
