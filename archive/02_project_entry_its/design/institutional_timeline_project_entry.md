# Institutional Timeline For UKB Project Entry

## Objective

This note reconstructs the institutional timeline for UK Biobank project entry before any project-entry ITS estimation. The design logic is:

```text
official institutional evidence
-> system-evolution timeline
-> externally justified periods / breakpoints
-> raw project-start trajectory
-> ITS design
```

The observed 2024 monthly starts are not used to decide which institutional periods existed. They are used only after the evidence-based dates and windows are fixed.

## Public "Start Date" Measurement

### What Is Directly Documented

UK Biobank's public existing-project pages display `Start date` and `Project status` fields. The existing-project index says it covers projects "already approved to access UK Biobank data" and warns that publication of updates can lag behind the underlying information.

Official access guidance documents the workflow before access:

- Application and registration precede access. The AMS user guide lists five stages before access to the UK Biobank Resource: Application, Registration, Access Committee review, Material Transfer Agreement, and Sample/Data Release.
- The access FAQ says access is granted only after formal approval, full payment, and a signed, returned, and UKB-executed MTA.
- A June 2024 FAQ says the average time from application submission to data release is 15 weeks.
- A June 2024 MTA/data-access FAQ says data access requires executed MTAs for the applicant institute and named collaborating institutes, plus invoice payment.
- RAP guidance says an AMS application marked `Approved` but not `Underway` is not enabled for RAP access.

Sources:

- Existing projects: https://www.ukbiobank.ac.uk/projects/
- AMS applying/registering guide: https://community.ukbiobank.ac.uk/hc/en-gb/articles/28023058927261-AMS-User-Guide-Registering
- Application/access FAQ: https://community.ukbiobank.ac.uk/hc/en-gb/articles/28002689502237-Applying-to-UK-Biobank-and-accessing-data-FAQ
- Submission-to-release FAQ: https://community.ukbiobank.ac.uk/hc/en-gb/articles/15006910060317-How-soon-do-I-get-access-to-the-data-after-I-have-submitted-my-application
- MTA-to-access FAQ: https://community.ukbiobank.ac.uk/hc/en-gb/articles/15015476800285-When-will-I-get-access-to-the-data-after-signing-the-MTA
- RAP enablement FAQ: https://community.ukbiobank.ac.uk/hc/en-gb/articles/22784123882909-Why-does-it-say-that-my-project-is-not-enabled-for-UKB-RAP

### What Is Strongly Implied

The public `Start date` is not the application submission date. The documented 15-week average lag from submission to data release rules out interpreting monthly `new_projects` as contemporaneous new applications.

The public `Start date` is also unlikely to be approval alone. UKB distinguishes approved applications from applications that are `Underway`; projects approved but not underway are not enabled for RAP. Payment, MTA execution, mandatory training, and RAP/AMS linkage are all potential gates between approval and operational access.

The safest interpretation is that `Start date` is closest to a recorded approved-project start or operational access date, likely near the AMS transition from approved-in-principle to started/underway and before or around data/RAP availability. Public evidence does not prove whether it is exactly payment completion, MTA execution, AMS `Underway`, first data dispense, or a manually recorded administrative start field.

### What Remains Unknown

The reviewed public sources do not define the internal data dictionary for the public `Start date` field. They do not state whether it is set automatically or manually, whether it is exactly the `Underway` status date, whether it equals first data release/dispense, or whether public-page publication lag can shift the visible date.

### Safest Paper Interpretation

Use `recorded UK Biobank project starts`, `publicly recorded project starts`, or `projects becoming operational in UKB records`. Do not call the outcome `new applications`. Do not interpret monthly counts as application submissions or approvals without further UKB administrative documentation.

## Reconstructed Project-Entry Pipeline

| Stage | Official terminology | Responsible actor | Existed before July 2024? | Changed during transition? | Plausible effect on recorded start timing |
| --- | --- | --- | --- | --- | --- |
| 1 | Application | Applicant PI/research team; UKB AMS | Yes | Application form and data-tier language moved into RAP-default context | Submission date is upstream and can be far earlier than public Start date. |
| 2 | Registration | Individual researchers; UKB Access Management Team | Yes | RAP account linkage became more central for operational access | Registration/recheck issues can delay collaborator/project readiness. |
| 3 | Scientific/access review; Access Committee review for relevant cases | UKB Access/Scientific teams; Access Committee | Yes | Exemption requests after RAP-default are reviewed through Access/Scientific teams and Access Committee | Review time affects approval but is not itself public Start date. |
| 4 | Approval | UKB Access/Scientific teams or Access Committee | Yes | Approval increasingly linked to RAP tier/default access path | Approval alone does not enable RAP if project is not Underway. |
| 5 | Access fee/payment | Applicant PI or institution; UKB finance/access teams | Yes | Fee notes now specify RAP-exclusive access with limited exemptions | Outstanding payment can delay data access and project start. |
| 6 | Material Transfer Agreement (MTA) | Applicant institute, collaborating institutes, UKB; DocuSign | Yes | New/updated MTA route and RAP-related MTA requests became more salient | Unsigned/unexecuted MTAs delay access and start timing. |
| 7 | Mandatory training | PI, lead collaborators, researchers; UKB training/onboarding team | Partly; RAP-specific mandatory training became central around transition | Three-course mandatory RAP training was introduced/made available, with existing-user deadline of 31 March 2025 | Training can gate access and create onboarding delays. |
| 8 | AMS project status | UKB access administrators; AMS | Yes | RAP enablement requires application status `Underway` | Most relevant public clue: Approved-but-not-underway projects are not enabled for RAP. |
| 9 | RAP account creation/linkage | Researcher; DNAnexus/UKB-RAP; AMS | RAP existed before July 2024 | Became the default access route for new projects and additional data | Account/linking frictions can delay operational readiness. |
| 10 | Data dispensing / project workspace | Researcher; UKB-RAP/DNAnexus; UKB Researcher Enablement | Yes for RAP projects; not default for all projects before July 2024 | Became the ordinary route for new data/project access | Usually short once prerequisites are met, but downstream of training/status. |
| 11 | Public recorded Start date | UKB public project system | Yes | Public date now records starts under a changed RAP-default access system | Best interpreted as recorded operational project start, not application submission. |

## Structured Evidence Table

| Date / period | Event | Official source | Source date | Process stage affected | Projects affected | Expected timing implication | Relevance to public Start date | Evidence strength | ITS use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| March 2012 onward | UKB data first made available to researchers. Fact: official release chronology dates the launch of available baseline data to March 2012. Interpretation: this defines the historical download/data-release regime. | Past data releases | Updated 21 Jan 2026 | Data release/access model | All projects | Long pre-period under non-RAP-default access | Context for the public series | HIGH | CONTEXT_ONLY |
| 2021 | UKB-RAP launched. Fact: UKB states the platform launched in 2021. Interpretation: July 2024 was not RAP birth, but a default-access transition. | RAP transition announcement | Edited 19 Nov 2024 | Access environment | RAP-using projects | Heterogeneous pre-2024 RAP exposure | Avoids overclaiming July 2024 | HIGH | CONTEXT_ONLY |
| July 2023 | OMOP available on RAP. Fact: official chronology lists OMOP release on RAP. Interpretation: some data pathways were already RAP-mediated. | Past data releases | Updated 21 Jan 2026 | Data modality/access | OMOP projects | Pre-transition RAP-oriented demand possible | Context only | MEDIUM | CONTEXT_ONLY |
| Late 2023 | Main 500k WGS release and RAP-only sequence-access context. Fact: release chronology lists WGS; transition announcement says genomic sequence data was already RAP-only. Interpretation: RAP-intensive projects predate the default switch. | Past data releases; RAP transition announcement | Updated 21 Jan 2026; edited 19 Nov 2024 | Genomic data access | WGS projects | Earlier RAP exposure for genomics | Context only | MEDIUM | CONTEXT_ONLY |
| Pre-access workflow | Application, registration, AC review, MTA, and sample/data release stages. Fact: AMS guide lists these five stages. Interpretation: project starts are downstream of submission. | AMS applying/registering guide | Updated 9 Apr 2026 | Full application-to-access pipeline | New applicants | Administrative stages create lags | Strong support against `new applications` label | HIGH | CONTEXT_ONLY |
| Pre-access workflow | Access requires approval, charges paid, and executed MTA. Fact: FAQ states these conditions. Interpretation: recorded starts likely occur after approval/payment/MTA gates. | Application/access FAQ | Updated 22 Jul 2025 | Approval, payment, MTA | Approved applications | Payment/MTA can delay starts | Strong support for operational-start interpretation | HIGH | CONTEXT_ONLY |
| 11 Jun 2024 | Average submission-to-data-release time is 15 weeks. Fact: UKB FAQ gives this average. Interpretation: application submissions cannot be read from monthly Start dates. | Submission-to-release FAQ | Updated 11 Jun 2024 | Submission to release | New applications | Long average administrative lag | High relevance to outcome naming | HIGH | CONTEXT_ONLY |
| 11 Jun 2024 | Fully signed/executed MTA and payment required for data access. Fact: UKB states this. Interpretation: institute-side processing can affect start timing. | MTA-to-access FAQ | Updated 11 Jun 2024 | MTA/payment/access | Applicant and collaborating institutes | Delays possible after approval | Strong support for downstream interpretation | HIGH | CONTEXT_ONLY |
| 5 Jul 2024 / July 2024 | All data for new projects and additional data for existing projects moved to UKB-RAP, with limited exceptions. Fact: UKB announcement states this. Interpretation: primary institutional breakpoint. | RAP transition announcement | Edited 19 Nov 2024; event used in current study metadata as 5 Jul 2024 | Access modality; onboarding; exemptions | New projects and additional-data requests | Operational access route changes from this point | Primary externally justified break | HIGH | PRIMARY_BREAKPOINT_CANDIDATE |
| July 2024 to Q4 2024 | UKB data would not be updated until Q4 2024 during the transition phase. Fact: announcement states this. Interpretation: supports broad transition context, not a project-start pause. | RAP transition announcement | Edited 19 Nov 2024 | Data-update schedule | Existing and newly approved projects | May affect demand/timing indirectly | Context for transition window | MEDIUM | SUPPORTED_TRANSITION_WINDOW |
| 6 Jun 2024 onward | RAP account creation requires approved AMS account, approved RAP application listing, and AMS-RAP linking. Fact: UKB states this. Interpretation: RAP onboarding adds operational gates. | RAP account creation guide | Created 6 Jun 2024; updated 8 Apr 2025 | Account/linking | RAP-enabled projects | Linkage frictions can delay access | Relevant but not exact Start date definition | HIGH | CONTEXT_ONLY |
| 4 Jul 2024 | Once training is complete and a researcher is using RAP, data usually dispenses within 24 hours. Fact: UKB states this. Interpretation: first data dispense is a final short step after upstream gates. | Up-and-running FAQ | Updated 4 Jul 2024 | Data dispensing | RAP projects | Short final access lag after prerequisites | Helps distinguish status from first data access | MEDIUM | CONTEXT_ONLY |
| 9-21 Oct 2024 | Mandatory on-demand training courses were released/made available. Fact: official comment says courses were released; UKB training post says researchers must complete three courses. Interpretation: October includes onboarding changes, but not an official restart. | Training forum post; training-now-available post | 9 Oct post, official comment edited 16 Oct; training post edited 14 Nov 2024 | Training/onboarding | RAP users and projects | Training availability can gate operations | Relevant to transition window | MEDIUM | SUPPORTED_TRANSITION_WINDOW |
| 31 Mar 2025 | Existing UKB-RAP users had to complete training by this deadline. Fact: UKB training post states the deadline. Interpretation: defensible end of training/onboarding compliance context. | Training-now-available post | Edited 14 Nov 2024 | Training compliance | Existing RAP users | Access may be paused until training complete | Secondary transition-context endpoint | HIGH | SUPPORTED_TRANSITION_WINDOW |
| March 2025 | First major listed post-transition release in available chronology. Fact: official list records March 2025 release. Interpretation: possible demand shock, not project-entry rule. | Past data releases | Updated 21 Jan 2026 | Data release | Projects needing new data | Could affect demand | Context only | MEDIUM | CONTEXT_ONLY |
| 2025 | Exemption policy and application process formalized/updated. Fact: UKB lists Access/Scientific and Access Committee review of exemption requests. Interpretation: ongoing RAP-default governance, not 2024 break. | Exemption policy; exemption application guide | Updated 3 Jul 2025 and 8 Oct 2025 | Exemption review | Nonstandard download requests | Extra review for exceptions | Context only | MEDIUM | CONTEXT_ONLY |
| January 2025 | Direct access applications from insurance companies no longer approved. Fact: UKB states policy changed after January 2025. Interpretation: narrow applicant-type rule. | Access to UKB data | Page last updated 23 Apr 2026 | Eligibility | Insurance-company applicants | Narrowly affects applicant composition | Limited aggregate relevance | MEDIUM | NOT_SUITABLE_FOR_ITS |
| May-June 2024 | Observed slowdown in recorded starts. Fact: repository data show May = 33 and June = 10. Interpretation: no independent official phase found. | Project-start data | Local generated data | Outcome series only | Recorded starts | Descriptive anomaly | Do not label institutional phase | LOW | NOT_SUITABLE_FOR_ITS |
| July-September 2024 | Observed trough in recorded starts. Fact: repository data show July = 3, August = 0, September = 1. Interpretation: overlaps the broader documented transition but is not a documented project-entry pause. | Project-start data | Local generated data | Outcome series only | Recorded starts | Descriptive anomaly | Exploratory only | LOW | NOT_SUITABLE_FOR_ITS |
| October 2024 | Observed rebound in recorded starts. Fact: repository data show October = 208. Interpretation: not documented as official restart or batch processing in reviewed sources. | Project-start data | Local generated data | Outcome series only | Recorded starts | Descriptive anomaly | Exploratory only | LOW | NOT_SUITABLE_FOR_ITS |

Machine-readable version: `analyses/interrupted_time_series/project_entry/data/project_entry_institutional_timeline.csv`.

## Observed-Data Labels

### May-June Slowdown

A. Independent official evidence for an actual institutional phase: No. I found no official source documenting a May-June 2024 project-entry slowdown, pause, application freeze, approval freeze, MTA freeze, or batching period.

B. Evidence for broader transition only: Yes, but only prospectively/structurally. The July 2024 announcement and June/July 2024 access guidance show a system preparing for RAP-default operations, but not a named May-June phase.

C. Outcome-defined pattern: Yes. The slowdown label is outcome-defined and should remain descriptive/exploratory.

### July-September Trough/Pause

A. Independent official evidence for an actual institutional phase: Partly for the broader RAP transition, no for an exact July-September project-entry pause. UKB explicitly identifies a transition to RAP-default access and says data updates were held until Q4 2024 during the transition phase.

B. Evidence for broader transition only: Yes. July 2024 onward is externally documented as the RAP-default transition. The exact July-September trough is not documented as a formal pause in applications, approvals, MTA execution, project activation, or RAP enablement.

C. Outcome-defined pattern: The trough window is outcome-defined. It can be shown as a raw anomaly overlaid on the institutionally documented July 2024 transition, but it should not be a primary ITS dummy.

### October Rebound/Restart

A. Independent official evidence for an actual institutional phase: No official restart, reopening, backlog-clearing, or batch-activation announcement was found for October 2024.

B. Evidence for broader transition only: Yes. Mandatory training availability appears in October 2024, and UKB's broader transition/onboarding process was active. This does not document an October project-entry restart.

C. Outcome-defined pattern: Yes. October 2024 is an observed rebound in recorded project starts, not a documented institutional restart.

## Implications for Project-Entry ITS

### A. Externally Justified Primary Breakpoint(s)

The primary breakpoint is July 2024, operationalized at the monthly level as July 2024 and later. The underlying institutional event is the 5 July 2024 RAP-default transition for all data for new projects and additional data for existing projects, with limited exceptions.

This is the only high-confidence project-entry breakpoint found in the reviewed official evidence.

### B. Externally Supported Transition Windows

Two transition contexts are defensible:

- July 2024 through Q4 2024: supported by the official transition announcement's statement that data updates would be held until Q4 2024 during the transition phase.
- July 2024 through March 2025: supported by the transition announcement plus mandatory training release and the 31 March 2025 existing-user training deadline.

The second window is broader and more relevant to onboarding/training, but it is less clean as a project-entry breakpoint because the March 2025 endpoint is a compliance deadline for existing UKB-RAP users, not a direct new-project activation date.

### C. Outcome-Defined Descriptive Episodes Only

May-June 2024 slowdown, July-September 2024 trough, and October 2024 rebound are raw-data episodes. They should be labelled as observed patterns unless future evidence documents an official administrative phase.

### D. Dates/Windows That Should Not Enter The Formal ITS

Do not include a May-June 2024 slowdown dummy, July-September 2024 pause dummy, or October 2024 restart dummy in the primary ITS. They may enter only a clearly separated exploratory/data-driven characterization.

Do not use January 2025 insurance-access policy or 2025 exemption-policy updates as aggregate project-entry ITS breakpoints. They are either narrow in scope or later governance context.

### Recommended Primary Breakpoint/Window

Use a July 2024 primary breakpoint, with `PostTransition_t = 1` for July 2024 onward in monthly models. The breakpoint is externally justified, official, system-wide for new projects/additional data, and plausibly affects the administrative path from approval to operational access.

As a secondary institutionally justified specification, consider a broad transition-window indicator for July 2024 through March 2025, or a transition-window exclusion/partialing approach, because official evidence supports transition/onboarding activity but not a precise July-September pause. The paper should say this design is descriptive and institutionally anchored, not causal.
