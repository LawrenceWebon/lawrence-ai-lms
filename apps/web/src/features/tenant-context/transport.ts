export type TenantCandidate = {
  id: string;
  slug: string;
  displayName: string;
  membershipStatus: "active";
};

export type ActiveTenant = Pick<TenantCandidate, "id" | "slug" | "displayName">;

export type TransportProblemCode =
  | "AUTHENTICATION_REQUIRED"
  | "INVITATION_INVALID"
  | "TENANT_ACCESS_DENIED"
  | "TENANT_ACCESS_INACTIVE"
  | "TRANSPORT_UNAVAILABLE";

export class TenantContextProblem extends Error {
  constructor(readonly code: TransportProblemCode) {
    super(code);
    this.name = "TenantContextProblem";
  }
}

export interface TenantContextTransport {
  signIn(credentials: { email: string; password: string }): Promise<TenantCandidate[]>;
  selectTenant(selector: string, candidates: TenantCandidate[]): Promise<ActiveTenant>;
  acceptInvitation(token: string): Promise<"accepted" | "already-accepted">;
  refreshAccess(candidates: TenantCandidate[]): Promise<TenantCandidate[]>;
  signOut(): void;
}
