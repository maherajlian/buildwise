# BuildWise public demo

[Start the in-app walkthrough](https://buildwise-1fy.pages.dev/guides/#walkthrough).
The fictional **Restaurant Booking & Customer Engagement SaaS** sample is
read-only and requires no account. If the free API is sleeping, wait for it
to start, then retry. Do not enter production data.

| Step | What to look for |
| --- | --- |
| [Read Discovery](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=discovery) | The structured brief explains the no-show problem, the users, and the targets for adoption and repeat visits. |
| [Check Requirements](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=requirements) | Find the P0 booking requirement; its criteria describe success and unavailable slots. |
| [Compare Architecture](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=architecture) | Open a category and an alternative to see rules, inputs, constraints and cost assumptions. |
| [Review Specs](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=specs) and [Plan](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=plan) | Compare the PRD with the technical design and user stories. Open a task's notes and criteria; check its dependencies before scheduling it. |
| [Inspect Testing](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=testing) and [Operations](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=operations) | Review proposed tests, risks, and SLOs. Proposed tests have not been executed. The operations view links to deployment and telemetry plans. |
| [Export from Overview](https://buildwise-1fy.pages.dev/projects/view/?id=sample&tab=overview) | Select **Export project pack (Markdown)** and read the brief, recommendations, specs, tasks and plans in one file. |

To create your own, open [Projects](https://buildwise-1fy.pages.dev/projects/).
Save discovery, add a requirement with an observable acceptance criterion, then
generate, edit and export the results. You can delete your project from Overview.
Keep the Markdown pack if you need a copy beyond this browser.

The [Observability demo](https://buildwise-1fy.pages.dev/observability/) shows
BuildWise's own live API and database status, separate from the sample's
suggested plans. The [runbook](operations/observability.md) shows how to see
traces and diagnose a controlled failure locally.
