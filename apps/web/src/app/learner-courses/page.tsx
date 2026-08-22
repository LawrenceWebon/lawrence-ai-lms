import { LearnerPlaybackExperience } from "../../features/learner-playback/learner-playback-experience";

type LearnerCoursesPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LearnerCoursesPage({ searchParams }: LearnerCoursesPageProps) {
  const params = await searchParams;
  const requestedScenario = params.scenario;
  const scenario = Array.isArray(requestedScenario) ? requestedScenario[0] : requestedScenario;

  return <LearnerPlaybackExperience scenario={scenario} />;
}
