% Options for packages loaded elsewhere
\PassOptionsToPackage{unicode}{hyperref}
\PassOptionsToPackage{hyphens}{url}
%
\documentclass[
]{article}
\usepackage{amsmath,amssymb}
\usepackage{iftex}
\ifPDFTeX
  \usepackage[T1]{fontenc}
  \usepackage[utf8]{inputenc}
  \usepackage{textcomp} % provide euro and other symbols
\else % if luatex or xetex
  \usepackage{unicode-math} % this also loads fontspec
  \defaultfontfeatures{Scale=MatchLowercase}
  \defaultfontfeatures[\rmfamily]{Ligatures=TeX,Scale=1}
\fi
\usepackage{lmodern}
\ifPDFTeX\else
  % xetex/luatex font selection
\fi
% Use upquote if available, for straight quotes in verbatim environments
\IfFileExists{upquote.sty}{\usepackage{upquote}}{}
\IfFileExists{microtype.sty}{% use microtype if available
  \usepackage[]{microtype}
  \UseMicrotypeSet[protrusion]{basicmath} % disable protrusion for tt fonts
}{}
\makeatletter
\@ifundefined{KOMAClassName}{% if non-KOMA class
  \IfFileExists{parskip.sty}{%
    \usepackage{parskip}
  }{% else
    \setlength{\parindent}{0pt}
    \setlength{\parskip}{6pt plus 2pt minus 1pt}}
}{% if KOMA class
  \KOMAoptions{parskip=half}}
\makeatother
\usepackage{xcolor}
\usepackage{color}
\usepackage{fancyvrb}
\newcommand{\VerbBar}{|}
\newcommand{\VERB}{\Verb[commandchars=\\\{\}]}
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\}}
% Add ',fontsize=\small' for more characters per line
\newenvironment{Shaded}{}{}
\newcommand{\AlertTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{#1}}}
\newcommand{\AnnotationTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\AttributeTok}[1]{\textcolor[rgb]{0.49,0.56,0.16}{#1}}
\newcommand{\BaseNTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\BuiltInTok}[1]{\textcolor[rgb]{0.00,0.50,0.00}{#1}}
\newcommand{\CharTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\CommentTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textit{#1}}}
\newcommand{\CommentVarTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\ConstantTok}[1]{\textcolor[rgb]{0.53,0.00,0.00}{#1}}
\newcommand{\ControlFlowTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{\textbf{#1}}}
\newcommand{\DataTypeTok}[1]{\textcolor[rgb]{0.56,0.13,0.00}{#1}}
\newcommand{\DecValTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\DocumentationTok}[1]{\textcolor[rgb]{0.73,0.13,0.13}{\textit{#1}}}
\newcommand{\ErrorTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{#1}}}
\newcommand{\ExtensionTok}[1]{#1}
\newcommand{\FloatTok}[1]{\textcolor[rgb]{0.25,0.63,0.44}{#1}}
\newcommand{\FunctionTok}[1]{\textcolor[rgb]{0.02,0.16,0.49}{#1}}
\newcommand{\ImportTok}[1]{\textcolor[rgb]{0.00,0.50,0.00}{\textbf{#1}}}
\newcommand{\InformationTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\newcommand{\KeywordTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{\textbf{#1}}}
\newcommand{\NormalTok}[1]{#1}
\newcommand{\OperatorTok}[1]{\textcolor[rgb]{0.40,0.40,0.40}{#1}}
\newcommand{\OtherTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{#1}}
\newcommand{\PreprocessorTok}[1]{\textcolor[rgb]{0.74,0.48,0.00}{#1}}
\newcommand{\RegionMarkerTok}[1]{#1}
\newcommand{\SpecialCharTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\SpecialStringTok}[1]{\textcolor[rgb]{0.73,0.40,0.53}{#1}}
\newcommand{\StringTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\VariableTok}[1]{\textcolor[rgb]{0.10,0.09,0.49}{#1}}
\newcommand{\VerbatimStringTok}[1]{\textcolor[rgb]{0.25,0.44,0.63}{#1}}
\newcommand{\WarningTok}[1]{\textcolor[rgb]{0.38,0.63,0.69}{\textbf{\textit{#1}}}}
\usepackage{longtable,booktabs,array}
\usepackage{calc} % for calculating minipage widths
% Correct order of tables after \paragraph or \subparagraph
\usepackage{etoolbox}
\makeatletter
\patchcmd\longtable{\par}{\if@noskipsec\mbox{}\fi\par}{}{}
\makeatother
% Allow footnotes in longtable head/foot
\IfFileExists{footnotehyper.sty}{\usepackage{footnotehyper}}{\usepackage{footnote}}
\makesavenoteenv{longtable}
\setlength{\emergencystretch}{3em} % prevent overfull lines
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\setcounter{secnumdepth}{-\maxdimen} % remove section numbering
\ifLuaTeX
  \usepackage{selnolig}  % disable illegal ligatures
\fi
\usepackage{bookmark}
\IfFileExists{xurl.sty}{\usepackage{xurl}}{} % add URL line breaks if available
\urlstyle{same}
\hypersetup{
  hidelinks,
  pdfcreator={LaTeX via pandoc}}

\author{}
\date{}

\begin{document}

{
\setcounter{tocdepth}{3}
\tableofcontents
}
\section{Employee Attendance Management
System}\label{employee-attendance-management-system}

\subsection{Project overview}\label{project-overview}

A web-based employee attendance and workforce management application
built with \textbf{FastAPI, PostgreSQL, SQLAlchemy and APScheduler}. It
centralizes attendance tracking, shifts, leave, work-from-home requests,
overtime, automated notifications and administrative reporting in a
role-based web interface.

\subsection{Table of contents}\label{table-of-contents}

\begin{itemize}
\tightlist
\item
  \hyperref[features]{Features}
\item
  \hyperref[user-roles]{User roles}
\item
  \hyperref[technology-stack]{Technology stack}
\item
  \hyperref[system-architecture]{System architecture}
\item
  \hyperref[overtime-and-email-workflows]{Overtime and email workflows}
\item
  \hyperref[installation-and-setup]{Installation and setup}
\item
  \hyperref[email-configuration]{Email configuration}
\item
  \hyperref[first-time-configuration]{First-time configuration}
\item
  \hyperref[background-automation]{Background automation}
\item
  \hyperref[attendance-finalization]{Attendance finalization}
\item
  \hyperref[api-documentation]{API documentation}
\item
  \hyperref[project-structure]{Project structure}
\item
  \hyperref[testing]{Testing}
\item
  \hyperref[security-and-deployment]{Security and deployment}
\item
  \hyperref[validation-and-known-limitations]{Validation and known
  limitations}
\end{itemize}

\subsection{Features}\label{features}

\subsubsection{Authentication and access
control}\label{authentication-and-access-control}

\begin{itemize}
\tightlist
\item
  JWT-based authentication and role-based authorization.
\item
  Super Admin, Manager and Employee accounts.
\item
  Password changes, administrative password resets and account
  activation/deactivation.
\item
  Protected API endpoints and role-specific frontend views.
\end{itemize}

\subsubsection{Employee management}\label{employee-management}

\begin{itemize}
\tightlist
\item
  Create, view and update employee profiles, employee codes, email
  addresses, departments and job titles.
\item
  Assign employees to managers and shifts; maintain reporting
  relationships.
\item
  Manage account status, joining dates and employee records.
\item
  Administrative attendance corrections and audit history.
\end{itemize}

\subsubsection{Attendance management}\label{attendance-management}

\begin{itemize}
\tightlist
\item
  Employee check-in and check-out with multiple working sessions per
  day.
\item
  Track worked minutes, required working hours, late arrivals and
  overtime.
\item
  Support office and WFH attendance modes.
\item
  Personal attendance history and manager team attendance views.
\item
  Identify missing check-outs, incomplete attendance and attendance
  conflicts.
\item
  Apply company-defined attendance thresholds when calculating daily
  results.
\end{itemize}

\subsubsection{Shift and holiday
management}\label{shift-and-holiday-management}

\begin{itemize}
\tightlist
\item
  Configure shift start/end times, required working duration and
  overnight shifts.
\item
  Assign employees to shifts and calculate attendance relative to their
  schedules.
\item
  Maintain holidays and company working-day policies.
\item
  Finalize employee-days according to their individual shift completion
  times.
\end{itemize}

\subsubsection{Leave management}\label{leave-management}

\begin{itemize}
\tightlist
\item
  Submit, edit and withdraw leave requests, including half-day leave.
\item
  Manager approval/rejection and configurable automatic approval
  policies.
\item
  Cancellation of approved leave through the applicable workflow.
\item
  Track leave balances and administrative allocations.
\item
  Monthly paid-leave accrual with annual caps and an
  accrual/carry-forward ledger.
\item
  Detect conflicts between attendance and approved leave.
\end{itemize}

\subsubsection{Work-from-home
management}\label{work-from-home-management}

\begin{itemize}
\tightlist
\item
  Submit WFH requests and view request status.
\item
  Enforce configured notice periods, monthly limits and
  overlapping-request checks.
\item
  Manager approval/rejection or policy-based auto-approval.
\item
  Track WFH usage and distinguish WFH attendance from office attendance.
\end{itemize}

\subsubsection{Overtime and forgotten check-out
management}\label{overtime-and-forgotten-check-out-management}

\begin{itemize}
\tightlist
\item
  Detect when an employee completes the required working duration while
  a session remains open.
\item
  Ask the employee to confirm overtime or check out.
\item
  Send configurable follow-up reminders when the employee does not
  respond.
\item
  Keep attendance open when overtime is confirmed and issue periodic
  overtime reminders.
\item
  Provisionally close unattended sessions after the configured reminder
  cycle.
\item
  Notify the employee, assigned manager and Super Admin as applicable.
\item
  Allow Super Admin review and correction of automatically closed
  attendance.
\end{itemize}

\subsubsection{In-app notifications}\label{in-app-notifications}

\begin{itemize}
\tightlist
\item
  Attendance, overtime, leave and WFH event notifications.
\item
  Action-required notifications for relevant attendance workflows.
\item
  Individual and bulk mark-as-read operations.
\item
  Resolve obsolete attendance actions when the associated session ends.
\end{itemize}

\subsubsection{Automated email
notifications}\label{automated-email-notifications}

\begin{itemize}
\tightlist
\item
  Send enabled notification categories to registered email addresses
  using SMTP.
\item
  Configure a global email switch and individual notification categories
  from Email Management.
\item
  Store outgoing messages in a database-backed email outbox.
\item
  Process queued emails through a background job instead of sending
  directly inside attendance requests.
\item
  Track pending, sent, failed and cancelled messages, delivery attempts
  and timestamps.
\item
  Retry transient delivery failures and allow Super Admin to requeue
  failed messages.
\item
  Revalidate live overtime reminders before sending to avoid sending
  obsolete reminders after checkout or state changes.
\item
  Send a test email to the signed-in Super Admin to validate SMTP
  configuration.
\end{itemize}

\subsubsection{Dashboards and analytics}\label{dashboards-and-analytics}

\begin{longtable}[]{@{}lll@{}}
\toprule\noalign{}
Employee dashboard & Manager dashboard & Super Admin dashboard \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Personal attendance and working hours & Team attendance and current work
status & Company-wide attendance and headcount \\
Monthly summary and trends & Shift-wise team breakdown & Department and
shift breakdowns \\
Attendance calendar and recent days & Late arrivals and overtime &
Monthly comparisons and trends \\
Leave balances and WFH usage & Pending requests and conflicts & Pending
approvals and auto-closure reviews \\
Upcoming requests and holidays & Upcoming team leave & Attendance rate,
punctuality, worked/required hours and overtime \\
\end{longtable}

Dashboard figures are calculated from attendance records and configured
working-day policies. Metric denominators, incomplete records and
future-date handling require validation before using these reports for
payroll or formal HR reporting.

\subsubsection{Administration and
automation}\label{administration-and-automation}

\begin{itemize}
\tightlist
\item
  Company settings, shifts, holidays and employee administration.
\item
  Leave allocations, attendance corrections and audit logs.
\item
  Configurable overtime reminder intervals and maximum reminder count.
\item
  Review automatically closed attendance and manage email delivery.
\item
  Manual execution of supported attendance, leave-accrual and overtime
  jobs.
\end{itemize}

\subsection{User roles}\label{user-roles}

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Role & Responsibilities \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\texttt{SUPER\_ADMIN} & Company configuration, employee management,
shifts, holidays, attendance corrections, leave allocations, company
analytics, automation, overtime review and email management \\
\texttt{MANAGER} & Team attendance monitoring, leave/WFH decisions,
attendance conflict resolution and team analytics \\
\texttt{EMPLOYEE} & Check-in/out, personal attendance, overtime
confirmation, leave/WFH requests, balances, notifications and personal
dashboard \\
\end{longtable}

\subsection{Technology stack}\label{technology-stack}

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Technology & Purpose \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Python & Backend implementation \\
FastAPI / Uvicorn & REST API and ASGI application server \\
SQLAlchemy & ORM and database sessions \\
PostgreSQL & Persistent application data \\
Alembic & Database schema migrations \\
APScheduler & Background and scheduled jobs \\
JWT / python-jose & Authentication tokens \\
Passlib / bcrypt & Password hashing \\
SMTP / Python smtplib & Email delivery \\
HTML, CSS, JavaScript & Built-in single-page web frontend \\
python-dotenv & Environment configuration \\
pytest / HTTPX & Automated API testing \\
Git / GitHub & Source control \\
\end{longtable}

\subsection{System architecture}\label{system-architecture}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{flowchart TD}
\NormalTok{    U[Employee / Manager / Super Admin] {-}{-}\textgreater{} UI[Web frontend]}
\NormalTok{    UI {-}{-}\textgreater{} API[FastAPI routers and authentication]}
\NormalTok{    API {-}{-}\textgreater{} S[Attendance and business services]}
\NormalTok{    S {-}{-}\textgreater{} DB[(PostgreSQL)]}
\NormalTok{    J[APScheduler] {-}{-}\textgreater{} S}
\NormalTok{    S {-}{-}\textgreater{} N[Notification service]}
\NormalTok{    N {-}{-}\textgreater{} DB}
\NormalTok{    N {-}{-}\textgreater{} O[Email outbox in PostgreSQL]}
\NormalTok{    J {-}{-}\textgreater{} E[Email delivery service]}
\NormalTok{    O {-}{-}\textgreater{} E}
\NormalTok{    E {-}{-}\textgreater{} SMTP[SMTP server]}
\NormalTok{    SMTP {-}{-}\textgreater{} R[Registered recipient email]}
\end{Highlighting}
\end{Shaded}

The frontend is served by FastAPI at \texttt{/app/}. API routers enforce
access rules and delegate business operations to database-backed
services. Scheduled jobs process attendance, leave accrual, overtime and
outgoing email independently of the browser.

\subsection{Overtime and email
workflows}\label{overtime-and-email-workflows}

\subsubsection{Overtime example}\label{overtime-example}

Assume eight required working hours, a 15-minute reminder interval and
three maximum reminders. An employee checks in at 09:00 and works
continuously:

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Approximate time & Action \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
09:00 & Check-in \\
17:00 & Required hours completed; initial overtime prompt \\
17:15 & First reminder if no response \\
17:30 & Second reminder if no response \\
17:45 & Third reminder if no response \\
18:00 & Next due cycle may provisionally close the session if still
unanswered \\
\end{longtable}

In the reviewed implementation, closure is recorded at the time the
required duration was reached, not at the time the closure job runs. The
day is marked \texttt{INCOMPLETE} pending review. If the employee
confirms overtime, the session remains open and periodic
confirmed-overtime reminders are scheduled (default example: 120
minutes). Checkout ends the active workflow. Actual times depend on
scheduler execution, shift rules, worked duration and email processing.

\subsubsection{Email categories}\label{email-categories}

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Category & Purpose \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\texttt{OVERTIME\_PROMPT} & Required working hours completed \\
\texttt{OVERTIME\_REMINDER} & Unanswered overtime/check-out prompt \\
\texttt{OVERTIME\_CHECK} & Confirmed overtime reminder \\
\texttt{OVERTIME\_CONFIRMED} & Overtime confirmation \\
\texttt{FORGOT\_CHECKOUT} & Forgotten checkout alert to manager \\
\texttt{AUTO\_CLOSED} & Provisional attendance closure \\
\texttt{AUTO\_CLOSED\_REVIEW} & Super Admin review required \\
\texttt{AUTO\_CLOSE\_REVIEWED} & Review completed \\
\texttt{ATTENDANCE\_CORRECTED} & Attendance correction \\
\texttt{LEAVE\_REQUEST}, \texttt{LEAVE\_DECISION} & Leave request and
decision \\
\texttt{WFH\_REQUEST}, \texttt{WFH\_DECISION} & WFH request and
decision \\
\end{longtable}

Leave/WFH emails and overtime confirmation are optional categories
disabled by default in the reviewed email service.

\subsubsection{Email delivery lifecycle}\label{email-delivery-lifecycle}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{flowchart TD}
\NormalTok{    A[Attendance or request event] {-}{-}\textgreater{} B[Create notification]}
\NormalTok{    B {-}{-}\textgreater{} C\{Email category enabled?\}}
\NormalTok{    C {-}{-} No {-}{-}\textgreater{} D[In{-}app notification only]}
\NormalTok{    C {-}{-} Yes {-}{-}\textgreater{} E[Queue eligible recipient email]}
\NormalTok{    E {-}{-}\textgreater{} F[Scheduled outbox processing]}
\NormalTok{    F {-}{-}\textgreater{} G\{Still eligible?\}}
\NormalTok{    G {-}{-} No {-}{-}\textgreater{} H[Cancelled]}
\NormalTok{    G {-}{-} Yes {-}{-}\textgreater{} I[SMTP delivery attempt]}
\NormalTok{    I {-}{-} Accepted {-}{-}\textgreater{} J[Sent]}
\NormalTok{    I {-}{-} Error {-}{-}\textgreater{} K\{Attempts exhausted?\}}
\NormalTok{    K {-}{-} No {-}{-}\textgreater{} L[Pending with backoff]}
\NormalTok{    L {-}{-}\textgreater{} F}
\NormalTok{    K {-}{-} Yes {-}{-}\textgreater{} M[Failed]}
\NormalTok{    M {-}{-}\textgreater{} N[Admin retry]}
\NormalTok{    N {-}{-}\textgreater{} F}
\end{Highlighting}
\end{Shaded}

The reviewed service attempts up to five deliveries before marking an
email failed, using exponential retry delays. \texttt{SENT} means the
SMTP server accepted the message, not that inbox delivery or reading is
guaranteed. Email delivery is not guaranteed exactly once if a process
fails after SMTP acceptance but before the database update.

\subsection{Installation and setup}\label{installation-and-setup}

\subsubsection{Prerequisites}\label{prerequisites}

\begin{itemize}
\tightlist
\item
  Python 3 (the development environment uses Python 3.12).
\item
  PostgreSQL running locally or on an accessible database server.
\item
  Git, and optionally PyCharm.
\item
  SMTP account and credentials if email delivery is required.
\end{itemize}

\subsubsection{1. Clone the repository}\label{1-clone-the-repository}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{git clone https}\OperatorTok{://}\NormalTok{github}\OperatorTok{.}\FunctionTok{com}\OperatorTok{/}\NormalTok{SujanMikkili}\OperatorTok{/}\NormalTok{employee{-}attendance{-}system}\OperatorTok{.}\FunctionTok{git}
\FunctionTok{cd}\NormalTok{ employee{-}attendance{-}system}
\end{Highlighting}
\end{Shaded}

For a private repository, authenticate with an account that has access.

\subsubsection{2. Create and activate a virtual
environment}\label{2-create-and-activate-a-virtual-environment}

Windows PowerShell:

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{python }\OperatorTok{{-}}\NormalTok{m venv }\OperatorTok{.}\FunctionTok{venv}
\OperatorTok{.}\NormalTok{\textbackslash{}}\OperatorTok{.}\FunctionTok{venv}\NormalTok{\textbackslash{}Scripts\textbackslash{}Activate}\OperatorTok{.}\FunctionTok{ps1}
\end{Highlighting}
\end{Shaded}

Linux/macOS: \texttt{python3\ -m\ venv\ .venv} followed by
\texttt{source\ .venv/bin/activate}.

\subsubsection{3. Install dependencies}\label{3-install-dependencies}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{python }\OperatorTok{{-}}\NormalTok{m pip install }\OperatorTok{{-}}\NormalTok{r requirements}\OperatorTok{.}\FunctionTok{txt}
\end{Highlighting}
\end{Shaded}

Use the PostgreSQL driver matching \texttt{DATABASE\_URL}. The reviewed
requirements include \texttt{psycopg2-binary}; if using
\texttt{postgresql+psycopg://}, install \texttt{psycopg{[}binary{]}} and
declare it in requirements.

\subsubsection{4. Configure the
environment}\label{4-configure-the-environment}

\begin{Shaded}
\begin{Highlighting}[]
\FunctionTok{Copy{-}Item} \OperatorTok{.}\FunctionTok{env}\OperatorTok{.}\FunctionTok{example} \OperatorTok{.}\FunctionTok{env}
\end{Highlighting}
\end{Shaded}

Example \texttt{.env} (replace placeholders locally):

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{DATABASE\_URL=postgresql://postgres:YOUR\_PASSWORD@localhost:5432/attendance\_system}
\NormalTok{SECRET\_KEY=REPLACE\_WITH\_RANDOM\_SECRET}
\NormalTok{ENABLE\_SCHEDULER=true}
\NormalTok{SMTP\_HOST=smtp.gmail.com}
\NormalTok{SMTP\_PORT=587}
\NormalTok{SMTP\_SECURITY=starttls}
\NormalTok{SMTP\_USER=}
\NormalTok{SMTP\_PASSWORD=}
\NormalTok{SMTP\_FROM=}
\NormalTok{APP\_URL=http://127.0.0.1:8000/app/}
\end{Highlighting}
\end{Shaded}

Generate a random secret with
\texttt{python\ -c\ "import\ secrets;\ print(secrets.token\_urlsafe(48))"}.
Never commit the populated \texttt{.env} file.

\subsubsection{5. Create the PostgreSQL database and apply
migrations}\label{5-create-the-postgresql-database-and-apply-migrations}

Create the database named in \texttt{DATABASE\_URL} using pgAdmin or
PostgreSQL tools. For a new empty database:

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{alembic upgrade head}
\end{Highlighting}
\end{Shaded}

For an existing database, back it up and inspect
\texttt{alembic\ current}, \texttt{alembic\ history} and the actual
schema before applying migrations. Do not blindly stamp \texttt{head}:
stamping records a revision without creating missing tables or columns.
Only stamp a revision when its schema is verified to exist.

For future model changes, review the generated migration before applying
it:

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{alembic revision }\OperatorTok{{-}{-}}\NormalTok{autogenerate }\OperatorTok{{-}}\NormalTok{m }\StringTok{"describe change"}
\NormalTok{alembic upgrade head}
\end{Highlighting}
\end{Shaded}

\subsubsection{6. Create the first Super
Admin}\label{6-create-the-first-super-admin}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{python create\_super\_admin}\OperatorTok{.}\FunctionTok{py}
\end{Highlighting}
\end{Shaded}

Use secure initial credentials. Review local helper scripts for
hardcoded credentials before sharing the repository.

\subsubsection{7. Start the application}\label{7-start-the-application}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{uvicorn main}\OperatorTok{:}\NormalTok{app }\OperatorTok{{-}{-}}\NormalTok{reload}
\end{Highlighting}
\end{Shaded}

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Resource & Local URL \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Web application & \url{http://127.0.0.1:8000/app/} \\
Swagger UI & \url{http://127.0.0.1:8000/docs} \\
ReDoc & \url{http://127.0.0.1:8000/redoc} \\
\end{longtable}

\subsection{Email configuration}\label{email-configuration}

For Gmail SMTP, enable two-step verification on an eligible Google
account and create an App Password. Configure the following in the local
\texttt{.env} file:

\begin{longtable}[]{@{}ll@{}}
\toprule\noalign{}
Variable & Example / purpose \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
\texttt{SMTP\_HOST} & \texttt{smtp.gmail.com} \\
\texttt{SMTP\_PORT} & \texttt{587} \\
\texttt{SMTP\_SECURITY} & \texttt{starttls} (or \texttt{ssl} with the
provider\textquotesingle s appropriate port) \\
\texttt{SMTP\_USER} & Sender\textquotesingle s email address \\
\texttt{SMTP\_PASSWORD} & App Password or provider-specific SMTP
credential \\
\texttt{SMTP\_FROM} & Authorized sender address \\
\texttt{APP\_URL} & Application link included in notification emails \\
\texttt{ENABLE\_SCHEDULER} & \texttt{true} for automatic queue
processing \\
\end{longtable}

Restart the backend after changing environment settings. Sign in as
Super Admin, open Email Management, send a test email, enable desired
categories and save. Monitor delivery history and retry failed messages
when appropriate.

A localhost \texttt{APP\_URL} works only on the machine hosting the app.
Use a reachable HTTPS application URL for recipients in a deployed
environment. A compatible corporate SMTP provider may be substituted for
Gmail.

\subsection{First-time configuration}\label{first-time-configuration}

\begin{enumerate}
\def\labelenumi{\arabic{enumi}.}
\tightlist
\item
  Sign in as Super Admin and configure company settings, timezone,
  working-day rules and attendance thresholds.
\item
  Create shifts with appropriate start/end times and required working
  minutes, including overnight shifts if needed.
\item
  Create managers and employees; assign reporting managers, departments
  and shifts.
\item
  Configure holidays, leave balances, accrual and WFH policies.
\item
  Configure overtime reminder intervals and maximum reminders.
\item
  Configure email categories and test SMTP delivery.
\item
  Test an employee check-in/out and a complete approval and overtime
  workflow.
\end{enumerate}

Older employee creation forms restrict shift names to Morning Shift and
Evening Shift. A dynamic shift selection correction was developed
separately; verify it is present in the deployed version before using
additional shift names.

\subsection{Background automation}\label{background-automation}

\begin{longtable}[]{@{}lll@{}}
\toprule\noalign{}
Job & Schedule in reviewed scheduler & Purpose \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
Attendance finalization & Every 15 minutes & Finalize eligible
employee-days based on shift completion and grace periods \\
Monthly leave accrual & First day of each month, 00:10 & Credit paid
leave according to company policy \\
Overtime cycle & Every minute & Detect required-hours completion, send
reminders and process provisional closure \\
Email outbox & Every minute & Process pending eligible emails and
retries \\
Startup catch-up & Once at startup & Recheck attendance finalization and
current-month accrual \\
\end{longtable}

The scheduler uses the company timezone. The reviewed finalization
service looks back seven days and defines a three-hour shift-end grace
period and a separate twelve-hour abandoned-session threshold. Exact
eligibility depends on the employee\textquotesingle s shift and
attendance state.

Run only one scheduler instance when deploying multiple application
processes. Background jobs require the backend to be running; closing
the browser does not stop them. Startup catch-up is not a guarantee that
every historical missed job will be replayed.

\subsection{Attendance finalization}\label{attendance-finalization}

Daily results include \texttt{PRESENT}, \texttt{HALF\_DAY},
\texttt{ABSENT}, \texttt{ON\_LEAVE}, \texttt{INCOMPLETE} and
\texttt{FLAGGED}.

\begin{itemize}
\tightlist
\item
  Weekends and holidays are handled according to working-day policy.
\item
  Approved full-day leave is recorded as \texttt{ON\_LEAVE}; conflicting
  attendance may be flagged for review.
\item
  Worked duration is evaluated against full-day, short-hours and
  half-day thresholds.
\item
  Half-day leave is evaluated together with worked duration.
\item
  Missing check-outs can result in incomplete attendance and a manager
  conflict.
\item
  Overtime-related provisional closures follow their own Super Admin
  review workflow.
\item
  Authorized administrators can correct attendance and maintain audit
  records.
\end{itemize}

\subsection{API documentation}\label{api-documentation}

Swagger UI at \texttt{/docs} provides the complete endpoint list,
request schemas and authentication requirements. Selected endpoints from
the reviewed implementation:

\begin{longtable}[]{@{}lll@{}}
\toprule\noalign{}
Method & Endpoint & Purpose \\
\midrule\noalign{}
\endhead
\bottomrule\noalign{}
\endlastfoot
GET & \texttt{/dashboard/me} & Personal dashboard \\
GET & \texttt{/dashboard/team} & Team or company dashboard \\
GET & \texttt{/notifications/} & List notifications \\
POST & \texttt{/notifications/read-all} & Mark notifications read \\
POST & \texttt{/notifications/\{notification\_id\}/read} & Mark one
notification read \\
GET & \texttt{/overtime/status} & Employee overtime status \\
POST & \texttt{/overtime/confirm} & Confirm overtime \\
GET / PUT & \texttt{/overtime/settings} & Read/update overtime settings
(update restricted to Super Admin) \\
POST & \texttt{/admin/jobs/overtime-cycle} & Trigger overtime
processing \\
POST & \texttt{/admin/jobs/finalize-day} & Trigger attendance
finalization \\
POST & \texttt{/admin/jobs/accrue-month} & Trigger leave accrual \\
GET & \texttt{/admin/auto-closed} & List provisional closures \\
POST & \texttt{/admin/auto-closed/\{prompt\_id\}/confirm} & Review a
provisional closure \\
GET / PUT & \texttt{/admin/email/settings} & Read/update email
settings \\
POST & \texttt{/admin/email/test} & Send test email \\
GET & \texttt{/admin/email/history} & Email delivery history \\
POST & \texttt{/admin/email/retry} & Requeue failed emails \\
\end{longtable}

\subsection{Project structure}\label{project-structure}

The following describes the reviewed email-enabled source layout; the
latest GitHub working copy may consolidate models or use different
module names.

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{employee{-}attendance{-}system/}
\NormalTok{├── main.py                  \# FastAPI entry point and scheduler lifecycle}
\NormalTok{├── database.py              \# Database connection and sessions}
\NormalTok{├── models.py                \# Core ORM models}
\NormalTok{├── models\_extra.py          \# Notification, overtime and email models in reviewed archive}
\NormalTok{├── create\_super\_admin.py    \# Initial administrator setup}
\NormalTok{├── routers/                 \# Authentication, attendance, admin, shifts, holidays,}
\NormalTok{│                            \# leave, WFH, conflicts, dashboard, notifications,}
\NormalTok{│                            \# overtime and email endpoints}
\NormalTok{├── services/}
\NormalTok{│   ├── approvals.py         \# Approval helpers}
\NormalTok{│   ├── jobs.py              \# Attendance finalization and leave accrual}
\NormalTok{│   ├── scheduler.py         \# Background job scheduling}
\NormalTok{│   ├── stats.py             \# Attendance statistics}
\NormalTok{│   ├── notifications.py     \# Notification generation}
\NormalTok{│   ├── overtime.py          \# Overtime workflow}
\NormalTok{│   └── email\_service.py     \# SMTP delivery and outbox processing}
\NormalTok{├── alembic/                 \# Database migrations}
\NormalTok{├── alembic.ini              \# Alembic configuration}
\NormalTok{├── frontend/index.html      \# Single{-}page web interface}
\NormalTok{├── tests/                   \# API tests}
\NormalTok{├── requirements.txt         \# Python dependencies}
\NormalTok{├── .env.example             \# Environment configuration template}
\NormalTok{├── .gitignore               \# Git exclusion rules}
\NormalTok{└── README.md                \# Project documentation}
\end{Highlighting}
\end{Shaded}

\subsection{Testing}\label{testing}

\begin{Shaded}
\begin{Highlighting}[]
\NormalTok{pytest}
\end{Highlighting}
\end{Shaded}

The original API test setup uses temporary SQLite. Use a dedicated
PostgreSQL test database for PostgreSQL-specific migrations, locking and
outbox concurrency behavior. Never run destructive tests against
production data.

Recommended integration scenarios: role restrictions, multiple
attendance sessions, overnight shifts, leave/WFH approvals, missed
checkout, overtime confirmation, all reminder stages, auto-closure
review, SMTP failure/retry, stale reminder cancellation, monthly accrual
and dashboard metric reconciliation.

\subsection{Security and deployment}\label{security-and-deployment}

\begin{itemize}
\tightlist
\item
  Keep \texttt{.env}, private keys, database dumps, employee exports and
  local virtual environments out of Git.
\item
  Use a strong secret key, hashed passwords and authorized role checks.
\item
  Do not hardcode SMTP credentials, database passwords or initial admin
  passwords in scripts or configuration templates.
\item
  Restrict access to email history and employee data; use appropriate
  retention and backup policies.
\item
  Use HTTPS, restricted CORS origins and a production-appropriate server
  configuration. Do not use \texttt{-\/-reload} in production.
\item
  Run a single scheduler instance or a separately coordinated background
  worker.
\item
  Review migration history and back up PostgreSQL before deployment.
\item
  GitHub hosts the source code; pushing to GitHub does not deploy the
  application or upload the live PostgreSQL database.
\end{itemize}

\subsection{Validation and known
limitations}\label{validation-and-known-limitations}

\begin{itemize}
\tightlist
\item
  SMTP test delivery and the initial overtime email were observed
  successfully during development. Full reminder lifecycle and
  failure/retry scenarios still require end-to-end testing.
\item
  Dashboard calculations are under review, including person-day
  denominators and reconciliation of late, absent and present counts.
\item
  Existing reminder deadlines may retain the interval used when they
  were created; verify the interval-change correction before relying on
  immediate rescheduling.
\item
  The latest working copy must use consistent email module names and
  model imports. Verify whether email/notification models are
  consolidated into \texttt{models.py} or remain in
  \texttt{models\_extra.py}.
\item
  Verify the active Alembic revision chain against the actual database
  schema before upgrading an existing installation.
\item
  Older employee creation code may enforce Gmail-only employee
  addresses; verify the current validation policy before onboarding
  corporate email accounts.
\end{itemize}

\end{document}
