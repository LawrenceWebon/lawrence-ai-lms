import { CourseEditorExperience } from "../../features/course-editor/course-editor-experience";

type CourseEditorPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function CourseEditorPage({ searchParams }: CourseEditorPageProps) {
  const params = await searchParams;
  const requestedScenario = params.scenario;
  const scenario = Array.isArray(requestedScenario) ? requestedScenario[0] : requestedScenario;

  return <CourseEditorExperience scenario={scenario} />;
}
