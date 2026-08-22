import { SourceAdmissionExperience } from "../../features/source-admission/source-admission-experience";

type SourceDocumentsPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SourceDocumentsPage({ searchParams }: SourceDocumentsPageProps) {
  const params = await searchParams;
  const requestedScenario = params.scenario;
  const scenario = Array.isArray(requestedScenario) ? requestedScenario[0] : requestedScenario;

  return <SourceAdmissionExperience scenario={scenario} />;
}
