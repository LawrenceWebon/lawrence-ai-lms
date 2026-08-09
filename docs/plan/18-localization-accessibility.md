# Localization, RTL, Time Zones, and Accessibility

Status: **WCAG 2.2 AA target approved; manual conformance evidence pending**  
Change ID: CHG-038

## Localization architecture

Separate:

1. Interface translation catalogs in version control.
2. Dynamic tenant and course translations in PostgreSQL.

Initial locales:

```text
en-PH
fil-PH
```

Design for future RTL locales such as Arabic.

## Locale fallback

```text
user preference
→ tenant default
→ course primary locale
→ platform default
```

## Dynamic content

Translation tables support:

- Course title and description
- Module and lesson titles
- Lesson content
- Quiz and assignment instructions
- Email templates
- Certificates
- CMS and legal pages
- AI-generated artifacts

AI-generated translation remains a draft until reviewed.

## Time handling

- Store all timestamps in UTC.
- Store IANA time-zone names.
- Render dates in the user time zone.
- Schedule live classes and deadlines using explicit time zone.
- Preserve original time zone in event records when needed.

## RTL

- Set document direction from locale metadata.
- Mirror layout, navigation, and directional icons where appropriate.
- Do not create a separate RTL application.
- Include RTL Playwright visual and interaction tests.

## Accessibility target

Target WCAG 2.2 AA.

Required:

- Keyboard navigation
- Visible focus
- Semantic headings
- Form labels and error associations
- Alternative text
- Caption and transcript support
- Color contrast
- Reduced motion support
- Screen-reader announcements for asynchronous job progress
- Accessible course player controls
- Accessible charts and downloadable tables

### Manual verification procedure (CHG-038)

For each critical journey and representative content type, record browser/OS/assistive-technology versions, tester, date, result, defect/evidence link and retest:

- automated axe scan as an aid, not conformance proof;
- keyboard-only operation, logical order, no trap, skip/navigation mechanisms and visible focus;
- screen-reader names/roles/states, headings/landmarks, form errors, live regions, tables and streamed/progress updates using at least the approved desktop/mobile combinations;
- 200% text zoom, 400% reflow, orientation, spacing, contrast, high-contrast/forced-colors and reduced motion;
- captions/transcripts/audio alternatives and accessible media controls;
- representative learner/instructor/admin testing, including validation/error/empty/loading/timeout states.

Exceptions record WCAG criterion, affected journey/users, severity, workaround/compensating control, owner, approver and expiry. An automated score cannot waive a failed A/AA criterion.

## AI accessibility

- Provide plain-language explanation option.
- Allow text-size and reading preferences.
- Ensure streamed answers are announced sensibly.
- Make citation links keyboard accessible.
