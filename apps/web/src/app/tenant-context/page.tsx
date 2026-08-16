import { TenantContextExperience } from "../../features/tenant-context/tenant-context-experience";

type TenantContextPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function TenantContextPage({ searchParams }: TenantContextPageProps) {
  const params = await searchParams;
  const requestedScenario = params.scenario;
  const scenario = Array.isArray(requestedScenario) ? requestedScenario[0] : requestedScenario;

  return <TenantContextExperience scenario={scenario} />;
}
