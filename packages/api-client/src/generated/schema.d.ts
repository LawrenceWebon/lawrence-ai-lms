// GENERATED from contracts/openapi/openapi.json; DO NOT EDIT.
export type RoleCode = "tenant_admin" | "instructor" | "reviewer" | "learner";
export type MembershipStatus = "active" | "inactive";
export type CourseStatus =
  | "draft"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "scheduled"
  | "published"
  | "withdrawn"
  | "archived";
export type CourseOrigin = "manual" | "ai_assisted";
export type ReviewerPolicy = "self_review_allowed" | "separate_reviewer_required";
export type ReviewDecision = "changes_requested" | "approved";
export type TransitionName =
  | "submit_review"
  | "request_changes"
  | "approve"
  | "publish"
  | "withdraw"
  | "archive";
export type RichTextMark = "strong" | "emphasis" | "code";
export type RightsBasis =
  | "owned"
  | "licensed"
  | "written_permission"
  | "public_domain"
  | "other_documented";
export type SourceAdmissionStatus =
  | "rights_pending"
  | "upload_pending"
  | "quarantined"
  | "validating"
  | "admitted"
  | "rejected"
  | "cancelled"
  | "blocked";
export type SourceAuthorizationStatus =
  | "requested"
  | "active"
  | "denied"
  | "revoked"
  | "expired"
  | "disputed";
export type SourceOperation = "store" | "extract" | "ocr" | "generate";
export type RequestedSourceOperation = "extract" | "ocr" | "generate";
export type IngestionStatus =
  | "queued"
  | "claimed"
  | "extracting"
  | "normalizing"
  | "quality_check"
  | "ready_for_generation"
  | "retryable"
  | "failed"
  | "cancelled"
  | "rights_blocked";
export type GenerationStatus =
  | "queued"
  | "planning"
  | "blueprint_review"
  | "generation_queued"
  | "generating"
  | "review_ready"
  | "canonicalized"
  | "rejected"
  | "retryable"
  | "failed"
  | "rights_blocked";
export type GenerationTargetLevel = "beginner" | "intermediate" | "advanced";
export type GenerationTeachingStyle = "concise" | "guided" | "reference";
export type GenerationRejectionReason =
  | "GENERATION_CONTENT_REJECTED"
  | "GENERATION_SOURCE_ALIGNMENT_REJECTED";
export type UploadIntentStatus = "active" | "consumed" | "expired" | "cancelled";
export type EnrollmentStatus = "active" | "revoked";
export type ProgressState = "not_started" | "in_progress" | "completed";
export type ProgressCommandName = "open_lesson" | "complete_lesson" | "reopen_lesson";

export interface paths {
  "/health": {
    parameters: EmptyParameters;
    get: operations["healthCheck"];
  };
  "/api/v1/auth-context": {
    parameters: EmptyParameters;
    get: operations["getAuthenticationContext"];
  };
  "/api/v1/tenant-invitations/accept": {
    parameters: EmptyParameters;
    post: operations["acceptTenantInvitation"];
  };
  "/api/v1/tenants/{tenant_id}/invitations": {
    parameters: EmptyParameters;
    post: operations["createTenantInvitation"];
  };
  "/api/v1/tenants/{tenant_id}/memberships": {
    parameters: EmptyParameters;
    get: operations["listTenantMemberships"];
  };
  "/api/v1/tenants/{tenant_id}/memberships/{membership_id}": {
    parameters: EmptyParameters;
    patch: operations["updateTenantMembership"];
  };
  "/api/v1/tenants/{tenant_id}/courses": {
    parameters: EmptyParameters;
    post: operations["createCourse"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions": {
    parameters: EmptyParameters;
    get: operations["listCourseVersions"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}": {
    parameters: EmptyParameters;
    get: operations["getCourseVersion"];
    patch: operations["updateCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/curriculum": {
    parameters: EmptyParameters;
    put: operations["replaceCourseCurriculum"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/submit-review": {
    parameters: EmptyParameters;
    post: operations["submitCourseReview"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/request-changes": {
    parameters: EmptyParameters;
    post: operations["requestCourseChanges"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/approve": {
    parameters: EmptyParameters;
    post: operations["approveCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/publish": {
    parameters: EmptyParameters;
    post: operations["publishCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/withdraw": {
    parameters: EmptyParameters;
    post: operations["withdrawCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/archive": {
    parameters: EmptyParameters;
    post: operations["archiveCourseVersion"];
  };
  "/api/v1/tenants/{tenant_id}/courses/{course_id}/versions/{version_id}/successor-draft": {
    parameters: EmptyParameters;
    post: operations["createSuccessorCourseDraft"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/admissions": {
    parameters: EmptyParameters;
    post: operations["createSourceAdmission"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}": {
    parameters: EmptyParameters;
    get: operations["getSourceAdmission"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/cancel": {
    parameters: EmptyParameters;
    post: operations["cancelSourceAdmission"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/rights-authorizations/{authorization_id}/decisions": {
    parameters: EmptyParameters;
    post: operations["reviewSourceStoreAuthorization"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/upload-intents": {
    parameters: EmptyParameters;
    post: operations["createSourceUploadIntent"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/authorizations": {
    parameters: EmptyParameters;
    get: operations["listSourceOperationAuthorizations"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/authorizations/{operation}": {
    parameters: EmptyParameters;
    post: operations["requestSourceOperationAuthorization"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/authorizations/{operation}/review": {
    parameters: EmptyParameters;
    post: operations["reviewSourceOperationAuthorization"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/ingestion-runs": {
    parameters: EmptyParameters;
    post: operations["startDocumentIngestion"];
  };
  "/api/v1/tenants/{tenant_id}/source-documents/{source_document_id}/versions/{source_version_id}/ingestion-runs/{run_id}": {
    parameters: EmptyParameters;
    get: operations["getDocumentIngestion"];
  };
  "/api/v1/tenants/{tenant_id}/course-generation-runs": {
    parameters: EmptyParameters;
    post: operations["startCourseGeneration"];
  };
  "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}": {
    parameters: EmptyParameters;
    get: operations["getCourseGeneration"];
  };
  "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}/approve-blueprint": {
    parameters: EmptyParameters;
    post: operations["approveCourseGenerationBlueprint"];
  };
  "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}/reject": {
    parameters: EmptyParameters;
    post: operations["rejectCourseGeneration"];
  };
  "/api/v1/tenants/{tenant_id}/course-generation-runs/{run_id}/canonicalize": {
    parameters: EmptyParameters;
    post: operations["canonicalizeCourseGeneration"];
  };
  "/api/v1/source-upload-targets/{opaque_token}": {
    parameters: EmptyParameters;
    put: operations["uploadSourceDocument"];
  };
  "/api/v1/tenants/{tenant_id}/enrollments": {
    parameters: EmptyParameters;
    post: operations["createEnrollment"];
  };
  "/api/v1/tenants/{tenant_id}/enrollments/{enrollment_id}/revoke": {
    parameters: EmptyParameters;
    post: operations["revokeEnrollment"];
  };
  "/api/v1/tenants/{tenant_id}/learner/courses": {
    parameters: EmptyParameters;
    get: operations["listLearnerCourses"];
  };
  "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/playback": {
    parameters: EmptyParameters;
    get: operations["getLearnerPlayback"];
  };
  "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/lessons/{lesson_id}": {
    parameters: EmptyParameters;
    get: operations["getLearnerLesson"];
  };
  "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/open-lesson": {
    parameters: EmptyParameters;
    post: operations["openLearnerLesson"];
  };
  "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/complete-lesson": {
    parameters: EmptyParameters;
    post: operations["completeLearnerLesson"];
  };
  "/api/v1/tenants/{tenant_id}/learner/enrollments/{enrollment_id}/progress/reopen-lesson": {
    parameters: EmptyParameters;
    post: operations["reopenLearnerLesson"];
  };
}

export interface components {
  schemas: {
    AcceptInvitationRequest: {
      invitation_token: string;
    };
    AuthenticationContextResponse: {
      "$schema": "https://contracts.ai-lms.local/f001/auth-context.v1.schema.json";
      principal: components["schemas"]["AuthenticationPrincipalResponse"];
      active_tenant: components["schemas"]["TenantSummaryResponse"] | null;
      membership: components["schemas"]["AuthenticationMembershipResponse"] | null;
      entitlement: components["schemas"]["EntitlementResponse"] | null;
      available_tenants: components["schemas"]["TenantCandidateResponse"][];
    };
    AuthenticationMembershipResponse: {
      id: string;
      status: MembershipStatus;
      row_version: number;
      role_codes: string[];
      permission_codes: string[];
    };
    AuthenticationPrincipalResponse: {
      user_id: string;
      authentication_time: string;
      assurance_level: "aal1" | "aal2";
    };
    CreateInvitationRequest: {
      email: string;
      role_codes: RoleCode[];
    };
    EntitlementResponse: {
      status: "active" | "expired" | "suspended";
      valid_until: string | null;
    };
    HealthResponse: {
      capabilities: string[];
      service: string;
      status: string;
    };
    InvitationReceiptResponse: {
      id: string;
      tenant_id: string;
      status: string;
      expires_at: string;
    };
    MembershipSummaryResponse: {
      id: string;
      tenant_id: string;
      status: string;
      row_version: number;
      role_codes: RoleCode[];
    };
    ProblemDetails: {
      type: string;
      title: string;
      status: number;
      detail: string;
      code: string;
      request_id: string;
      errors: Record<string, unknown>[];
    };
    TenantCandidateResponse: components["schemas"]["TenantSummaryResponse"] & {
      membership_status: MembershipStatus;
    };
    TenantSummaryResponse: {
      id: string;
      slug: string;
      display_name: string;
    };
    UpdateMembershipRequest: {
      status?: MembershipStatus | null;
      role_codes?: RoleCode[] | null;
      row_version: number;
    };
    TextNode: {
      type: "text";
      text: string;
      marks: RichTextMark[];
    };
    ParagraphNode: {
      type: "paragraph";
      content: components["schemas"]["TextNode"][];
    };
    HeadingNode: {
      type: "heading";
      level: 2 | 3 | 4;
      content: components["schemas"]["TextNode"][];
    };
    ListItemNode: {
      type: "list_item";
      content: components["schemas"]["ParagraphNode"][];
    };
    BulletListNode: {
      type: "bullet_list";
      items: components["schemas"]["ListItemNode"][];
    };
    OrderedListNode: {
      type: "ordered_list";
      items: components["schemas"]["ListItemNode"][];
    };
    RichTextDocument: {
      type: "document";
      content: Array<
        | components["schemas"]["ParagraphNode"]
        | components["schemas"]["HeadingNode"]
        | components["schemas"]["BulletListNode"]
        | components["schemas"]["OrderedListNode"]
      >;
    };
    CurriculumBlockV1: {
      id?: string;
      expected_row_version?: number;
      kind: "rich_text";
      position: number;
      document: components["schemas"]["RichTextDocument"];
    };
    CurriculumLessonV1: {
      id?: string;
      expected_row_version?: number;
      title: string;
      position: number;
      is_required: boolean;
      content_blocks: components["schemas"]["CurriculumBlockV1"][];
    };
    CurriculumSectionV1: {
      id?: string;
      expected_row_version?: number;
      title: string;
      position: number;
      lessons: components["schemas"]["CurriculumLessonV1"][];
    };
    CreateCourseV1: {
      slug: string;
      primary_locale: string;
      title: string;
      description: string;
    };
    UpdateCourseVersionV1: {
      expected_version_row_version: number;
      primary_locale?: string;
      title?: string;
      description?: string;
    };
    ReplaceCurriculumV1: {
      expected_version_row_version: number;
      sections: components["schemas"]["CurriculumSectionV1"][];
    };
    TransitionCourseVersionV1: {
      transition: TransitionName;
      expected_version_row_version: number;
      expected_course_row_version?: number;
      expected_content_hash: string;
      reason_code?: string;
      reason_codes?: string[];
    };
    CreateSuccessorDraftV1: {
      expected_course_row_version: number;
      expected_source_version_row_version: number;
      expected_source_content_hash: string;
    };
    CourseRecordV1: {
      id: string;
      tenant_id: string;
      slug: string;
      reviewer_policy: ReviewerPolicy;
      current_published_version_id: string | null;
      instructor_membership_ids: string[];
      row_version: number;
    };
    CourseVersionRecordV1: {
      id: string;
      tenant_id: string;
      course_id: string;
      predecessor_version_id: string | null;
      version_number: number;
      status: CourseStatus;
      origin_type: CourseOrigin;
      primary_locale: string;
      title: string;
      description: string;
      content_hash: string;
      submitted_hash: string | null;
      approved_hash: string | null;
      row_version: number;
    };
    ContentBlockRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      lesson_id: string;
      kind: "rich_text";
      position: number;
      row_version: number;
      document: components["schemas"]["RichTextDocument"];
    };
    LessonRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      section_id: string;
      title: string;
      position: number;
      is_required: boolean;
      row_version: number;
      content_blocks: components["schemas"]["ContentBlockRecordV1"][];
    };
    SectionRecordV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      title: string;
      position: number;
      row_version: number;
      lessons: components["schemas"]["LessonRecordV1"][];
    };
    CourseReviewV1: {
      id: string;
      tenant_id: string;
      course_version_id: string;
      decision: ReviewDecision;
      reviewed_hash: string;
      reviewer_id: string;
      self_review: boolean;
      reason_codes: string[];
      decided_at: string;
    };
    CourseSnapshotV1: {
      "$schema": "https://contracts.ai-lms.local/f002/canonical-course.v1.schema.json";
      course: components["schemas"]["CourseRecordV1"];
      version: components["schemas"]["CourseVersionRecordV1"];
      sections: components["schemas"]["SectionRecordV1"][];
      latest_review: components["schemas"]["CourseReviewV1"] | null;
    };
    CourseVersionSummaryV1: {
      id: string;
      tenant_id: string;
      course_id: string;
      predecessor_version_id: string | null;
      version_number: number;
      status: CourseStatus;
      title: string;
      content_hash: string;
      row_version: number;
      is_current_published: boolean;
    };
    CourseVersionHistoryV1: {
      tenant_id: string;
      course_id: string;
      current_published_version_id: string | null;
      versions: components["schemas"]["CourseVersionSummaryV1"][];
      next_cursor: string | null;
    };
    SuccessorDraftResultV1: {
      source_version_id: string;
      successor_version_id: string;
      snapshot: components["schemas"]["CourseSnapshotV1"];
    };
    CreateEnrollmentV1: {
      learner_membership_id: string;
      course_id: string;
    };
    RevokeEnrollmentV1: {
      expected_enrollment_row_version: number;
      reason_code: string;
    };
    EnrollmentV1: {
      id: string;
      tenant_id: string;
      learner_membership_id: string;
      course_id: string;
      course_version_id: string;
      admission_source: "manual_assignment";
      status: EnrollmentStatus;
      enrolled_at: string;
      revoked_at: string | null;
      row_version: number;
    };
    CourseProgressV1: {
      state: ProgressState;
      required_lesson_count: number;
      completed_required_lesson_count: number;
      resume_lesson_id: string | null;
      row_version: number;
    };
    DashboardCardV1: {
      enrollment_id: string;
      course_id: string;
      course_version_id: string;
      course_version_number: number;
      primary_locale: string;
      title: string;
      description: string;
      content_hash: string;
      enrolled_at: string;
      progress: components["schemas"]["CourseProgressV1"];
    };
    LearnerDashboardV1: {
      tenant_id: string;
      items: components["schemas"]["DashboardCardV1"][];
      next_cursor: string | null;
    };
    OutlineLessonV1: {
      id: string;
      title: string;
      position: number;
      is_required: boolean;
      progress_state: ProgressState;
    };
    OutlineSectionV1: {
      id: string;
      title: string;
      position: number;
      lessons: components["schemas"]["OutlineLessonV1"][];
    };
    PlaybackSnapshotV1: {
      tenant_id: string;
      enrollment_id: string;
      course_id: string;
      course_version_id: string;
      course_version_number: number;
      primary_locale: string;
      title: string;
      description: string;
      content_hash: string;
      sections: components["schemas"]["OutlineSectionV1"][];
      progress: components["schemas"]["CourseProgressV1"];
    };
    LessonContentBlockV1: {
      id: string;
      kind: "rich_text";
      position: number;
      document: components["schemas"]["RichTextDocument"];
    };
    LessonDetailV1: {
      id: string;
      section_id: string;
      title: string;
      position: number;
      is_required: boolean;
      progress_state: ProgressState;
      content_blocks: components["schemas"]["LessonContentBlockV1"][];
    };
    LessonPlaybackV1: {
      tenant_id: string;
      enrollment_id: string;
      course_version_id: string;
      primary_locale: string;
      content_hash: string;
      lesson: components["schemas"]["LessonDetailV1"];
      previous_lesson_id: string | null;
      next_lesson_id: string | null;
      progress: components["schemas"]["CourseProgressV1"];
    };
    ProgressCommandV1: {
      command: ProgressCommandName;
      lesson_id: string;
      expected_progress_row_version: number;
    };
    ProgressResultV1: {
      tenant_id: string;
      enrollment_id: string;
      course_version_id: string;
      lesson_id: string;
      lesson_state: ProgressState;
      course_state: ProgressState;
      required_lesson_count: number;
      completed_required_lesson_count: number;
      resume_lesson_id: string | null;
      progress_row_version: number;
      updated_at: string;
    };
    CreateRightsDeclarationV1: {
      basis: RightsBasis;
      attestation_version: "f003-source-rights-attestation-v1";
      attested: true;
      rights_holder_name?: string;
      evidence_reference?: string;
      valid_until?: string;
    };
    CreateSourceAdmissionV1: {
      display_name: string;
      declared_filename: string;
      rights_declaration: components["schemas"]["CreateRightsDeclarationV1"];
    };
    ReviewSourceStoreAuthorizationV1: {
      decision: "activate" | "deny" | "revoke";
      expected_authorization_row_version: number;
      decision_code:
        | "RIGHTS_EVIDENCE_ACCEPTED"
        | "RIGHTS_EVIDENCE_INSUFFICIENT"
        | "RIGHTS_REVOKED";
    };
    ReviewSourceOperationAuthorizationV1: {
      decision: "activate" | "deny" | "revoke";
      expected_authorization_row_version: number;
      decision_code:
        | "RIGHTS_EVIDENCE_ACCEPTED"
        | "RIGHTS_EVIDENCE_INSUFFICIENT"
        | "RIGHTS_REVOKED";
    };
    CancelSourceAdmissionV1: {
      expected_source_version_row_version: number;
      reason_code: "USER_CANCELLED" | "SOURCE_REPLACED";
    };
    SourceDocumentV1: {
      id: string;
      tenant_id: string;
      display_name: string;
      current_version_id: string;
      row_version: number;
    };
    SourceVersionV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      version_number: number;
      admission_status: SourceAdmissionStatus;
      declared_filename: string;
      content_sha256: string | null;
      derived_file_size_bytes: number | null;
      derived_media_type: string | null;
      derived_pdf_signature_valid: boolean | null;
      derived_parser_accepted: boolean | null;
      derived_page_count: number | null;
      derived_max_rendered_pixels_per_page: number | null;
      derived_rendered_pixels_total: number | null;
      derived_decoded_parser_bytes: number | null;
      derived_local_inspection_result: "accepted" | "unsafe" | "unavailable" | null;
      rejection_code: string | null;
      validation_attempt_count: number;
      row_version: number;
    };
    RightsDeclarationV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      declared_by_actor_id: string;
      basis: RightsBasis;
      attestation_version: "f003-source-rights-attestation-v1";
      attested_at: string;
      valid_until: string | null;
      evidence_reference: string | null;
      row_version: number;
    };
    SourceUseAuthorizationV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      rights_declaration_id: string;
      operation: "store";
      status: SourceAuthorizationStatus;
      requested_by_actor_id: string;
      reviewed_by_actor_id: string | null;
      decision_code: string | null;
      valid_from: string | null;
      valid_until: string | null;
      row_version: number;
    };
    SourceOperationAuthorizationV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      rights_declaration_id: string;
      operation: SourceOperation;
      status: SourceAuthorizationStatus;
      requested_by_actor_id: string;
      reviewed_by_actor_id: string | null;
      decision_code: string | null;
      valid_from: string | null;
      valid_until: string | null;
      row_version: number;
    };
    DocumentIngestionRunV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      status: IngestionStatus;
      parser_version: string;
      configuration_version: string;
      locale: "en";
      attempt_count: number;
      max_attempts: number;
      checkpoint: string;
      input_manifest_sha256: string;
      output_manifest_sha256: string | null;
      reason_code: string | null;
      quality_summary: Record<string, unknown>;
      row_version: number;
      created_at: string;
      updated_at: string;
    };
    StartCourseGenerationV1: {
      source_document_id: string;
      source_version_id: string;
      ingestion_run_id: string;
      target_level: GenerationTargetLevel;
      target_duration_minutes: number;
      intended_audience: string;
      teaching_style: GenerationTeachingStyle;
      locale: "en";
      supersedes_run_id?: string | null;
    };
    ApproveGenerationBlueprintV1: {
      expected_run_row_version: number;
      blueprint_id: string;
      blueprint_revision: number;
      expected_blueprint_content_sha256: string;
    };
    RejectCourseGenerationV1: {
      expected_run_row_version: number;
      expected_review_content_sha256: string;
      reason_code: GenerationRejectionReason;
    };
    CanonicalizeCourseGenerationV1: {
      expected_run_row_version: number;
      expected_output_manifest_sha256: string;
      course_slug: string;
    };
    GenerationCanonicalizationV1: {
      id: string;
      tenant_id: string;
      generation_run_id: string;
      course_id: string;
      course_version_id: string;
      reviewed_output_sha256: string;
      canonical_content_sha256: string;
      canonicalization_sha256: string;
      canonicalized_by_actor_id: string;
      created_at: string;
    };
    CourseGenerationRunV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      ingestion_run_id: string;
      supersedes_run_id: string | null;
      status: GenerationStatus;
      target_level: GenerationTargetLevel;
      target_duration_minutes: number;
      intended_audience: string;
      teaching_style: GenerationTeachingStyle;
      locale: "en";
      adapter: "deterministic-source-course-v1";
      provider: "local_deterministic";
      model: "none";
      input_manifest_sha256: string;
      blueprint_content_sha256: string | null;
      output_manifest_sha256: string | null;
      attempt_count: number;
      max_attempts: number;
      checkpoint: string;
      reason_code: string | null;
      row_version: number;
      created_at: string;
      updated_at: string;
    };
    CourseBlueprintItemV1: {
      id: string;
      kind: "module" | "lesson";
      parent_id: string | null;
      position: number;
      title: string;
      description: string;
      source_section_id: string;
    };
    CourseBlueprintV1: {
      id: string;
      schema_version: "course-blueprint.v1";
      title: string;
      description: string;
      intended_audience: string;
      prerequisites: string[];
      learning_outcomes: string[];
      items: components["schemas"]["CourseBlueprintItemV1"][];
      projection: Record<string, unknown>;
      content_sha256: string;
    };
    GeneratedLessonV1: {
      id: string;
      schema_version: "course-draft.v1";
      blueprint_lesson_item_id: string;
      source_section_id: string;
      title: string;
      document: Record<string, unknown>;
      content_sha256: string;
    };
    CourseGenerationReviewPackageV1: {
      run: components["schemas"]["CourseGenerationRunV1"];
      blueprint: components["schemas"]["CourseBlueprintV1"] | null;
      lessons: components["schemas"]["GeneratedLessonV1"][];
    };
    UploadIntentSummaryV1: {
      id: string;
      status: UploadIntentStatus;
      expires_at: string;
    };
    RemovalV1: {
      status: "not_required" | "pending" | "completed" | "failed";
      reason_code: "USER_CANCELLED" | "RIGHTS_REVOKED" | "RIGHTS_EXPIRED" | "RIGHTS_DISPUTED" | null;
    };
    SourceAdmissionV1: {
      source_document: components["schemas"]["SourceDocumentV1"];
      source_version: components["schemas"]["SourceVersionV1"];
      rights_declaration: components["schemas"]["RightsDeclarationV1"];
      store_authorization: components["schemas"]["SourceUseAuthorizationV1"];
      upload_intent: components["schemas"]["UploadIntentSummaryV1"] | null;
      removal: components["schemas"]["RemovalV1"];
    };
    UploadIntentV1: {
      id: string;
      tenant_id: string;
      source_document_id: string;
      source_version_id: string;
      status: UploadIntentStatus;
      target_url: string;
      expires_at: string;
      max_bytes: 6291456;
      accepted_media_type: "application/pdf";
      row_version: number;
    };
  };
}

export interface operations {
  healthCheck: {
    parameters: EmptyParameters;
    requestBody?: never;
    responses: { 200: JsonResponse<components["schemas"]["HealthResponse"]> };
  };
  getAuthenticationContext: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["AuthenticationContextResponse"]>;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  acceptTenantInvitation: {
    parameters: AuthParameters;
    requestBody: JsonRequest<components["schemas"]["AcceptInvitationRequest"]>;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"]>;
      401: ProblemResponse;
      404: ProblemResponse;
      410: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  createTenantInvitation: {
    parameters: {
      query?: never;
      header: AuthHeaders & { "Idempotency-Key": string; "X-Tenant-ID"?: string | null };
      path: { tenant_id: string };
      cookie?: never;
    };
    requestBody: JsonRequest<components["schemas"]["CreateInvitationRequest"]>;
    responses: {
      201: JsonResponse<components["schemas"]["InvitationReceiptResponse"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  listTenantMemberships: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path: { tenant_id: string };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"][]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  updateTenantMembership: {
    parameters: {
      query?: never;
      header?: AuthHeaders & { "X-Tenant-ID"?: string | null };
      path: { tenant_id: string; membership_id: string };
      cookie?: never;
    };
    requestBody: JsonRequest<components["schemas"]["UpdateMembershipRequest"]>;
    responses: {
      200: JsonResponse<components["schemas"]["MembershipSummaryResponse"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  createCourse: {
    parameters: CourseCollectionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateCourseV1"]>;
    responses: {
      201: JsonResponse<components["schemas"]["CourseSnapshotV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getCourseVersion: {
    parameters: CourseVersionParameters;
    requestBody?: never;
    responses: CourseSnapshotResponses;
  };
  listCourseVersions: {
    parameters: CourseHistoryParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["CourseVersionHistoryV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  updateCourseVersion: {
    parameters: CourseVersionParameters;
    requestBody: JsonRequest<components["schemas"]["UpdateCourseVersionV1"]>;
    responses: CourseSnapshotResponses;
  };
  replaceCourseCurriculum: {
    parameters: CourseVersionParameters;
    requestBody: JsonRequest<components["schemas"]["ReplaceCurriculumV1"]>;
    responses: CourseSnapshotResponses;
  };
  submitCourseReview: CourseTransitionOperation;
  requestCourseChanges: CourseTransitionOperation;
  approveCourseVersion: CourseTransitionOperation;
  publishCourseVersion: CourseTransitionOperation;
  withdrawCourseVersion: CourseTransitionOperation;
  archiveCourseVersion: CourseTransitionOperation;
  createSuccessorCourseDraft: {
    parameters: CourseVersionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateSuccessorDraftV1"]>;
    responses: {
      200: JsonResponse<components["schemas"]["SuccessorDraftResultV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  createEnrollment: {
    parameters: EnrollmentCollectionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateEnrollmentV1"]>;
    responses: {
      201: JsonResponse<components["schemas"]["EnrollmentV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  revokeEnrollment: {
    parameters: EnrollmentCommandParameters;
    requestBody: JsonRequest<components["schemas"]["RevokeEnrollmentV1"]>;
    responses: EnrollmentResponses;
  };
  listLearnerCourses: {
    parameters: LearnerCourseListParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["LearnerDashboardV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getLearnerPlayback: {
    parameters: LearnerEnrollmentParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["PlaybackSnapshotV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getLearnerLesson: {
    parameters: LearnerLessonParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["LessonPlaybackV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  openLearnerLesson: LearnerProgressOperation;
  completeLearnerLesson: LearnerProgressOperation;
  reopenLearnerLesson: LearnerProgressOperation;
  createSourceAdmission: {
    parameters: SourceCollectionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CreateSourceAdmissionV1"]>;
    responses: {
      201: JsonResponse<components["schemas"]["SourceAdmissionV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getSourceAdmission: {
    parameters: SourceVersionParameters;
    requestBody?: never;
    responses: SourceSnapshotResponses;
  };
  reviewSourceStoreAuthorization: {
    parameters: SourceAuthorizationCommandParameters;
    requestBody: JsonRequest<components["schemas"]["ReviewSourceStoreAuthorizationV1"]>;
    responses: SourceSnapshotResponses;
  };
  createSourceUploadIntent: {
    parameters: SourceVersionCommandParameters;
    requestBody?: never;
    responses: {
      201: JsonResponse<components["schemas"]["UploadIntentV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      429: ProblemResponse;
      500: ProblemResponse;
    };
  };
  uploadSourceDocument: {
    parameters: {
      query?: never;
      header?: never;
      path: { opaque_token: string };
      cookie?: never;
    };
    requestBody: BinaryRequest;
    responses: {
      202: JsonResponse<components["schemas"]["SourceAdmissionV1"]>;
      404: ProblemResponse;
      409: ProblemResponse;
      410: ProblemResponse;
      422: ProblemResponse;
      503: ProblemResponse;
      500: ProblemResponse;
    };
  };
  cancelSourceAdmission: {
    parameters: SourceVersionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CancelSourceAdmissionV1"]>;
    responses: SourceSnapshotResponses;
  };
  listSourceOperationAuthorizations: {
    parameters: SourceVersionParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["SourceOperationAuthorizationV1"][]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      500: ProblemResponse;
    };
  };
  requestSourceOperationAuthorization: {
    parameters: SourceOperationCommandParameters;
    requestBody?: never;
    responses: SourceOperationAuthorizationResponses;
  };
  reviewSourceOperationAuthorization: {
    parameters: SourceOperationCommandParameters;
    requestBody: JsonRequest<components["schemas"]["ReviewSourceOperationAuthorizationV1"]>;
    responses: SourceOperationAuthorizationResponses;
  };
  startDocumentIngestion: {
    parameters: SourceVersionCommandParameters;
    requestBody?: never;
    responses: {
      202: JsonResponse<components["schemas"]["DocumentIngestionRunV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getDocumentIngestion: {
    parameters: DocumentIngestionParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["DocumentIngestionRunV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      500: ProblemResponse;
    };
  };
  startCourseGeneration: {
    parameters: GenerationCollectionCommandParameters;
    requestBody: JsonRequest<components["schemas"]["StartCourseGenerationV1"]>;
    responses: {
      202: JsonResponse<components["schemas"]["CourseGenerationRunV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
  getCourseGeneration: {
    parameters: GenerationRunParameters;
    requestBody?: never;
    responses: {
      200: JsonResponse<components["schemas"]["CourseGenerationReviewPackageV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      500: ProblemResponse;
    };
  };
  approveCourseGenerationBlueprint: {
    parameters: GenerationRunCommandParameters;
    requestBody: JsonRequest<components["schemas"]["ApproveGenerationBlueprintV1"]>;
    responses: GenerationRunResponses;
  };
  rejectCourseGeneration: {
    parameters: GenerationRunCommandParameters;
    requestBody: JsonRequest<components["schemas"]["RejectCourseGenerationV1"]>;
    responses: GenerationRunResponses;
  };
  canonicalizeCourseGeneration: {
    parameters: GenerationRunCommandParameters;
    requestBody: JsonRequest<components["schemas"]["CanonicalizeCourseGenerationV1"]>;
    responses: {
      201: JsonResponse<components["schemas"]["GenerationCanonicalizationV1"]>;
      400: ProblemResponse;
      401: ProblemResponse;
      403: ProblemResponse;
      404: ProblemResponse;
      409: ProblemResponse;
      422: ProblemResponse;
      500: ProblemResponse;
    };
  };
}

type EmptyParameters = {
  query?: never;
  header?: never;
  path?: never;
  cookie?: never;
};
type AuthHeaders = { Authorization?: string | null };
type AuthParameters = {
  query?: never;
  header?: AuthHeaders;
  path?: never;
  cookie?: never;
};
type CourseHeaders = AuthHeaders & { "X-Tenant-ID": string };
type CourseCollectionCommandParameters = {
  query?: never;
  header: CourseHeaders & { "Idempotency-Key": string };
  path: { tenant_id: string };
  cookie?: never;
};
type CourseVersionParameters = {
  query?: never;
  header: CourseHeaders;
  path: { tenant_id: string; course_id: string; version_id: string };
  cookie?: never;
};
type CourseVersionCommandParameters = Omit<CourseVersionParameters, "header"> & {
  header: CourseHeaders & { "Idempotency-Key": string };
};
type CourseHistoryParameters = {
  query?: { cursor?: string | null; limit?: number };
  header: CourseHeaders;
  path: { tenant_id: string; course_id: string };
  cookie?: never;
};
type CourseSnapshotResponses = {
  200: JsonResponse<components["schemas"]["CourseSnapshotV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type CourseTransitionOperation = {
  parameters: CourseVersionCommandParameters;
  requestBody: JsonRequest<components["schemas"]["TransitionCourseVersionV1"]>;
  responses: CourseSnapshotResponses;
};
type LearningHeaders = AuthHeaders & { "X-Tenant-ID": string };
type EnrollmentCollectionCommandParameters = {
  query?: never;
  header: LearningHeaders & { "Idempotency-Key": string };
  path: { tenant_id: string };
  cookie?: never;
};
type LearnerEnrollmentParameters = {
  query?: never;
  header: LearningHeaders;
  path: { tenant_id: string; enrollment_id: string };
  cookie?: never;
};
type EnrollmentCommandParameters = Omit<LearnerEnrollmentParameters, "header"> & {
  header: LearningHeaders & { "Idempotency-Key": string };
};
type LearnerCourseListParameters = {
  query?: { cursor?: string | null; limit?: number };
  header: LearningHeaders;
  path: { tenant_id: string };
  cookie?: never;
};
type LearnerLessonParameters = Omit<LearnerEnrollmentParameters, "path"> & {
  path: LearnerEnrollmentParameters["path"] & { lesson_id: string };
};
type LearnerProgressParameters = Omit<LearnerEnrollmentParameters, "header"> & {
  header: LearningHeaders & { "Idempotency-Key": string };
};
type EnrollmentResponses = {
  200: JsonResponse<components["schemas"]["EnrollmentV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type LearnerProgressOperation = {
  parameters: LearnerProgressParameters;
  requestBody: JsonRequest<components["schemas"]["ProgressCommandV1"]>;
  responses: {
    200: JsonResponse<components["schemas"]["ProgressResultV1"]>;
    400: ProblemResponse;
    401: ProblemResponse;
    403: ProblemResponse;
    404: ProblemResponse;
    409: ProblemResponse;
    422: ProblemResponse;
    500: ProblemResponse;
  };
};
type SourceHeaders = AuthHeaders & { "X-Tenant-ID": string };
type SourceCollectionCommandParameters = {
  query?: never;
  header: SourceHeaders & { "Idempotency-Key": string };
  path: { tenant_id: string };
  cookie?: never;
};
type SourceVersionParameters = {
  query?: never;
  header: SourceHeaders;
  path: { tenant_id: string; source_document_id: string; source_version_id: string };
  cookie?: never;
};
type SourceVersionCommandParameters = Omit<SourceVersionParameters, "header"> & {
  header: SourceHeaders & { "Idempotency-Key": string };
};
type SourceAuthorizationCommandParameters = Omit<SourceVersionCommandParameters, "path"> & {
  path: SourceVersionParameters["path"] & { authorization_id: string };
};
type SourceOperationCommandParameters = Omit<SourceVersionCommandParameters, "path"> & {
  path: SourceVersionParameters["path"] & { operation: RequestedSourceOperation };
};
type DocumentIngestionParameters = Omit<SourceVersionParameters, "path"> & {
  path: SourceVersionParameters["path"] & { run_id: string };
};
type GenerationHeaders = AuthHeaders & { "X-Tenant-ID": string };
type GenerationCollectionCommandParameters = {
  query?: never;
  header: GenerationHeaders & { "Idempotency-Key": string };
  path: { tenant_id: string };
  cookie?: never;
};
type GenerationRunParameters = {
  query?: never;
  header: GenerationHeaders;
  path: { tenant_id: string; run_id: string };
  cookie?: never;
};
type GenerationRunCommandParameters = Omit<GenerationRunParameters, "header"> & {
  header: GenerationHeaders & { "Idempotency-Key": string };
};
type GenerationRunResponses = {
  200: JsonResponse<components["schemas"]["CourseGenerationRunV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type SourceOperationAuthorizationResponses = {
  200: JsonResponse<components["schemas"]["SourceOperationAuthorizationV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type SourceSnapshotResponses = {
  200: JsonResponse<components["schemas"]["SourceAdmissionV1"]>;
  400: ProblemResponse;
  401: ProblemResponse;
  403: ProblemResponse;
  404: ProblemResponse;
  409: ProblemResponse;
  422: ProblemResponse;
  500: ProblemResponse;
};
type JsonRequest<T> = { content: { "application/json": T } };
type BinaryRequest = { content: { "application/pdf": Blob | ArrayBuffer | Uint8Array } };
type JsonResponse<T> = {
  headers: Record<string, unknown>;
  content: { "application/json": T };
};
type ProblemResponse = {
  headers: Record<string, unknown>;
  content: {
    "application/json": components["schemas"]["ProblemDetails"];
    "application/problem+json": components["schemas"]["ProblemDetails"];
  };
};
