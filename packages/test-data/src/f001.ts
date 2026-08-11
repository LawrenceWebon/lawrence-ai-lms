export type MembershipStatus = "active" | "inactive";

export interface TenantCandidateFixture {
  id: string;
  slug: string;
  displayName: string;
  membershipStatus: MembershipStatus;
}

export const alphaTenant: TenantCandidateFixture = {
  id: "00000000-0000-4000-8000-0000000000a1",
  slug: "alpha",
  displayName: "Alpha Learning",
  membershipStatus: "active",
};

export const betaTenant: TenantCandidateFixture = {
  id: "00000000-0000-4000-8000-0000000000b1",
  slug: "beta",
  displayName: "Beta Learning",
  membershipStatus: "active",
};
