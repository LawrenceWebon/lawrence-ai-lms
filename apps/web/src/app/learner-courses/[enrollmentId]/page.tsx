import { LearnerPlaybackExperience } from "../../../features/learner-playback/learner-playback-experience";

type LearnerPlaybackPageProps = {
  params: Promise<{ enrollmentId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function LearnerPlaybackPage({
  params,
  searchParams,
}: LearnerPlaybackPageProps) {
  const { enrollmentId } = await params;
  const query = await searchParams;
  const requestedScenario = query.scenario;
  const scenario = Array.isArray(requestedScenario) ? requestedScenario[0] : requestedScenario;

  return <LearnerPlaybackExperience requestedEnrollmentId={enrollmentId} scenario={scenario} />;
}
