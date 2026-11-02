Ledger-Eval: Testing How Reliable AI Models Are With Money

Can we really trust AI models with people’s money?

That’s the question I wanted to explore when I started building Ledger-Eval.

Ledger-Eval is an evaluation framework I built to test how well AI models handle real-world financial engineering problems and Nigerian financial regulations.

It focuses on areas where getting something slightly wrong can have serious consequences: payment processing, financial calculations, database transactions, and tax compliance.

The goal wasn’t just to see whether AI could generate working code or produce convincing answers. I wanted to find out whether those answers were actually correct.

⸻

Why I Built This

AI models have become remarkably good at writing code and solving technical problems. But financial systems are different. A small mistake in a payment workflow, ledger calculation, or tax rule can lead to lost money, incorrect charges, or compliance issues.

I initially tested models against practical engineering problems involving failed payouts, duplicate transactions, refunds, and PostgreSQL behaviour.

The results were surprisingly strong.

This led me to explore another area: how well do these models understand financial rules that are specific to Nigeria?

I introduced tasks based on the Nigeria Tax Act 2025 to investigate this.

The results revealed an interesting gap. Models that performed exceptionally well on general engineering tasks sometimes struggled with specific Nigerian tax provisions, particularly where one provision limits or overrides another.

That became the central focus of Ledger-Eval.

At a Glance

	
Project	Ledger-Eval
Domain	Nigerian Fintech and Financial Engineering
Evaluation Tasks	12
Models Tested	3 Claude models
Total Trials	108
Grading	Deterministic, code-based grading
PostgreSQL Testing	Real PostgreSQL server
Tax Reference	Nigeria Tax Act 2025

Key Results

Across 108 trials:

Model	Average Score
Claude Opus 5.5	100.0%
Claude Sonnet 5.5	97.2%
Claude Haiku 5.5	93.0%

The interesting part wasn’t just the overall scores. It was the difference between how the models performed on general engineering problems and Nigerian tax compliance.

For example, Sonnet scored 98.4% on engineering tasks but 88.6% on Nigerian tax tasks.

Haiku scored 98.7% and 79.6%, respectively.

Opus passed every task in the final evaluation.

These results suggest that strong general engineering ability doesn’t always translate into equally strong performance when specialised local regulations are involved.

⸻

Video Walkthrough

Watch the project demonstration

The walkthrough covers the evaluation process, grading system, model comparisons, and some of the mistakes discovered during testing.

⸻

What Does Ledger-Eval Test?

Ledger-Eval contains 12 tasks grouped around three main areas:

1. Financial engineering and payment systems.
2. PostgreSQL behaviour and database reliability.
3. Nigerian tax laws and financial compliance.

Each task presents a realistic problem. The model must provide a solution, and the evaluation system checks whether that solution meets the expected requirements.

Here is a breakdown of the tasks.

1. Financial Engineering (Tasks 1–6)

These tasks focus on problems developers encounter when building financial applications and payment infrastructure.

Task	What It Tests	What Makes It Challenging
t1_payout_executor	Reliable payout processing	Handles timeouts, duplicate requests, provider delays, and situations where a payment’s actual outcome is unknown.
t2_webhook_convergence	Webhook processing	Tests whether a system can handle duplicate and out-of-order payment events without corrupting transaction records.
t3_fx_refund	Foreign currency refunds	Tests exchange rates, currency conversion, rounding, and accurate financial records.
t4_interest_backvalue	Interest calculations	Handles transactions that are backdated and require recalculating historical interest without changing existing records.
t5_wallet_repair	Wallet debugging	Presents a wallet with multiple underlying problems and tests whether the model can identify and fix all of them rather than just the obvious symptom.
t6_settlement_recon	Payment reconciliation	Tests whether the model can reconcile payment processor records with internal financial records, including chargebacks and corrected transactions.

2. PostgreSQL and Database Reliability (Tasks 7–10)

Financial applications depend heavily on databases. A system might work perfectly when one person uses it but behave differently when multiple transactions happen simultaneously.

These tasks test how well models understand PostgreSQL’s actual behaviour.

Task	What It Tests	What Makes It Challenging
t7_pg_concurrency	Database concurrency	Tests how PostgreSQL handles simultaneous transactions, locks, and conflicting updates.
t8_pg_locks	Database locking	Covers foreign keys, triggers, savepoints, and different locking scenarios.
t9_pg_isolation	Transaction isolation	Tests snapshots, serialization failures, constraints, and transaction behaviour.
t10_pg_money_time	Financial calculations and time	Covers rounding, floating-point behaviour, month-end dates, time zones, daylight-saving transitions, and ISO weeks.

3. Nigerian Tax and Financial Compliance (Tasks 11–12)

This is where the evaluation becomes particularly interesting.

I wanted to see whether AI models could correctly apply Nigerian financial regulations without simply relying on rules provided in their prompts.

The tasks are based on the Nigeria Tax Act 2025.

Task	What It Tests	What Makes It Challenging
t11_ng_tax_rules	Nigerian tax rules	Tests stamp duty, personal income tax, company tax, VAT, and chargeable gains. The model must determine the applicable rules without being given the actual provisions.
t12_ng_tax_interactions	Multiple tax provisions working together	Tests situations involving exemptions, income limits, previous-year deductions, crypto losses, and minimum effective tax rates.

For these tasks, the answers are tied to specific sections of the gazetted Act.

I also avoided questions where conflicting interpretations could make the expected answer debatable.

⸻

How the Evaluation Works

One thing I wanted to get right was the grading process.

I didn’t want another AI model deciding whether a model’s answer was correct. That could introduce another layer of uncertainty.

Instead, I built deterministic graders that check answers against predefined requirements.

In simple terms, each task has specific conditions that a correct solution must satisfy.

A solution receives partial credit for the checks it passes, and a full pass only happens when every required check succeeds.

Some of the things I implemented:

* Automated grading: Every task is evaluated using code rather than an AI judge.
* Failure injection: Payment tasks simulate failures at different stages to see whether the model’s solution can recover safely.
* Real PostgreSQL verification: Database answers are compared against actual behaviour from PostgreSQL 14.18.
* Tax references: Nigerian tax answers are checked against provisions of the Nigeria Tax Act 2025.
* Isolated execution: Submitted model code runs in a restricted child process with resource limits and network access disabled.

Testing the Graders Themselves

I also wanted to make sure the grading system wasn’t incorrectly rejecting valid solutions or accepting incorrect ones.

So I built a separate validation script:

python validate_graders.py

The validation produced the following results:

* All 12 reference solutions passed.
* Two alternative payout implementations also passed.
* 84 deliberately incorrect solutions were tested.
* Every incorrect solution failed the specific check it was designed to break.

During development, reviewing model outputs also helped me identify problems in some of my own grading rules.

For example, one of the original payout checks rejected a valid implementation. After reviewing the transcript, I corrected the grader and kept that implementation as a permanent regression test.

This was an important part of the process: the evaluation system itself needed to be reliable.

⸻

Models Tested and Results

Evaluation date: 31 October 2026

I tested three Claude models, running each against all 12 tasks with three independent trials per task.

That gave me 108 trials in total.

Overall Results

Model	Trials	Full Pass Rate	pass^k	pass@k	Average Score	Equivalent API Cost
Claude Opus 5.5	36	100%	12/12	12/12	100.0%	$8.70
Claude Sonnet 5.5	36	75%	8/12	10/12	97.2%	$2.61
Claude Haiku 5.5	36	50%	5/12	7/12	93.0%	$0.32

A quick explanation of the two metrics:

* pass^k: The number of tasks the model passed in all three trials.
* pass@k: The number of tasks the model passed at least once across the three trials.

Performance by Task Category

This is where the differences become more interesting.

Task Category	Opus	Sonnet	Haiku
Financial Engineering	100.0%	98.4%	98.7%
PostgreSQL	100.0%	99.7%	91.2%
Nigerian Tax Law	100.0%	88.6%	79.6%

The results show that all three models performed strongly on general financial engineering problems.

However, performance dropped when the models had to apply specific Nigerian tax provisions.

This was particularly noticeable with Sonnet and Haiku.

⸻

What Went Wrong? Some Interesting Examples

I didn’t just look at the final scores. I also reviewed the actual model outputs to understand why certain tasks failed.

Two examples stood out.

Example 1: Life Insurance Premium Deductions

Task: t12_ng_tax_interactions

The model was asked to calculate a tax deduction involving life insurance premiums.

Under the Act, the deduction is based on the premium paid in the preceding year.

However, Sonnet and Haiku repeatedly used the premium paid in the current year instead.

Both models made this mistake in all three trials.

The interesting part is that they understood the general tax calculation but missed the timing requirement.

Sonnet transcript | Haiku transcript

Example 2: Compensation for Loss of Employment

Task: t11_ng_tax_rules

In another scenario, an employee received ₦70 million as compensation for losing their job.

Sonnet and Haiku treated the entire amount as tax-exempt.

However, the exemption is subject to a ₦50 million limit under another provision of the Act.

That means ₦20 million should be chargeable.

Again, both models made the same mistake in all three trials.

This showed a weakness in how they handled provisions that depend on or override other sections of the law.

Sonnet transcript | Haiku transcript

Other Failures

There were also interesting mistakes in the PostgreSQL tasks.

For example:

* Haiku struggled with certain transaction isolation and locking scenarios.
* Some models made mistakes involving daylight-saving time and exact financial calculations.
* Sonnet had one payout task where its implementation passed the money-safety checks but returned an unexpected internal status.

The complete failure analysis and transcripts are available in the repository.

⸻

What I Learned

One of the biggest things I took away from building Ledger-Eval is that understanding the general rule isn’t always enough.

A model might understand how to calculate income tax but still miss an exemption limit. It might understand a payment workflow but fail when transactions arrive in an unexpected order.

The Nigerian tax results were particularly interesting.

Sonnet scored 98.4% on engineering tasks where the rules were stated, but 88.6% on Nigerian tax tasks where it had to apply the legislation itself.

This suggests that providing models with the actual governing documents could improve reliability.

I haven’t tested that directly yet, and the two task categories also differ in other ways, so I wouldn’t treat it as a proven conclusion.

Another important observation is that Opus passed every task in the final evaluation.

This means Ledger-Eval doesn’t demonstrate that every AI model struggles with these problems. Instead, it highlights specific weaknesses in the models tested and shows why evaluation needs to go beyond overall accuracy.

What I’d Like to Explore Next

There are several directions I’d like to take this project:

* Test more models from different providers.
* Expand the Nigerian financial and regulatory scenarios.
* Investigate whether providing the actual legislation improves model performance.
* Introduce more complex, multi-step financial tasks.
* Explore how models behave when they need to use tools and make decisions across several stages.

The bigger goal is to make financial AI systems easier to evaluate before they are trusted with real-world decisions.

⸻

Running Ledger-Eval Locally

If you’d like to explore the project or run the evaluations yourself, you can get started with Python 3.10 or later.

No Docker installation is required.

1. Clone the repository

git clone https://github.com/haybraham360/Eval_FinanceSolution.git
cd Eval_FinanceSolution

2. Create a virtual environment

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Validate the graders

You can run the grader validation without an API key:

python validate_graders.py

5. Reproduce the included results

You can re-grade the saved model outputs without making new API calls:

python run_eval.py regrade

The results will be available in:

results/final/summary.md

Running Your Own Model Evaluations

There are two supported approaches.

Option 1: Using Claude Code CLI

If you’re already logged in to the Claude CLI, you can run:

python run_eval.py run --run-id my-run --models cli-opus,cli-sonnet,cli-haiku

Option 2: Using OpenRouter

Copy the example environment file:

cp .env.example .env

Add your OpenRouter API key to .env, then run:

python run_eval.py run --run-id my-run --models claude-opus-5.5,gpt-6.1-sol,gemini-4-argon,grok-4.7

The API key is read from the environment or .env file.

You can also use --tasks and --trials to run selected tasks or reduce the number of trials.

Interrupted runs can be resumed using the same --run-id.

Verifying PostgreSQL Scenarios

If you want to reproduce the PostgreSQL tests against a local server, run:

python verify_postgres.py
python verify_scenarios.py

These scripts create and remove a temporary database named:

ledger_eval_verify

Make sure you understand this behaviour before running them on a database environment containing important data.

⸻

Runtime and Evaluation Cost

The final evaluation involved 108 trials and took approximately one hour of active execution time using three parallel workers.

The run was split across two sessions because the first session was interrupted. Previously completed trials were saved, and the remaining trials were resumed.

The run cost $0 on top of an existing Claude Pro subscription, using the plan’s available limits.

For reference, the CLI reported approximately $11.63 in equivalent API usage:

Model	Equivalent Cost
Opus	$8.70
Sonnet	$2.61
Haiku	$0.32
Total	$11.63

⸻

Limitations and Things to Keep in Mind

I want to be clear about what this evaluation does and doesn’t demonstrate.

* Only Claude models were tested. The results shouldn’t be used to rank Claude against other providers.
* The evaluation is limited to 12 tasks. These scenarios cover important areas, but they don’t represent every possible financial engineering or compliance problem.
* Opus passed all final trials. The results don’t demonstrate a failure in the strongest model tested.
* The tax evaluation is specific to the Nigeria Tax Act 2025. It shouldn’t be treated as a complete test of Nigerian tax compliance.
* Providing the actual legislation wasn’t tested as a separate experiment. Although the results suggest this could help, further testing is needed.
* Model usage reporting had limitations. The CLI reported Haiku usage alongside Opus and Sonnet in the evaluation runs. A separate test of Opus showed only Opus usage, but the saved raw files don’t contain a complete token breakdown. The harness has since been updated to capture this for future runs.

I believe documenting these limitations is just as important as presenting the results.

⸻

Project Structure

Some of the important directories and files:

ledger-eval/
│
├── tasks/                  # Evaluation task definitions
├── reference/              # Reference solutions and sources
├── graders/                # Deterministic grading logic
├── mutants/                # Deliberately incorrect solutions
├── results/
│   └── final/               # Final evaluation results
├── transcripts/
│   └── final/               # Model response transcripts
│
├── validate_graders.py      # Validate the grading system
├── run_eval.py              # Run and re-grade evaluations
├── verify_postgres.py       # PostgreSQL verification
├── verify_scenarios.py      # Scenario verification
├── models.json              # Model configurations
├── requirements.txt         # Python dependencies
└── README.md

⸻

References and Sources

The project was developed during the Micro1 hackathon.

The evaluation tasks and engineering scenarios were developed specifically for this project. The engineering test data is synthetic.

Some of the ideas behind the evaluation methodology were informed by the Micro1 participant guide and existing evaluation research, including:

* Terminal-Bench
* SWE-bench Verified
* τ-bench
* Anthropic’s Demystifying Evals for AI Agents

For the technical reference points:

* PostgreSQL results are based on PostgreSQL 14.18 behaviour.
* Nigerian tax answers are based on the Nigeria Tax Act 2025 (No. 7, Official Gazette No. 117, 26 June 2025).
* Individual Nigerian tax references are documented in reference/t11_sources.md.

⸻

How I Used AI During Development

I led the development of Ledger-Eval, from identifying the problem and deciding what to evaluate to reviewing the results and making changes to the evaluation system.

I used AI coding tools as part of the development process to help with drafting and implementing some of the tasks, graders, reference solutions, evaluation scripts, and documentation.

However, the direction of the project, the evaluation approach, the choice of financial scenarios, and the decisions made throughout development were mine.

I reviewed the tasks, checked the reference answers against the relevant provisions of the Nigeria Tax Act, tested the grading system, and examined the model transcripts to identify and correct issues.

The evaluation results and conclusions presented here are based on the tests I ran and the evidence collected during development.

⸻

Final Thoughts

Ledger-Eval started with a simple question: how reliable are AI models when money is involved?

Building it gave me an opportunity to explore that question through practical engineering challenges, database behaviour, and Nigerian financial regulations.

The biggest lesson for me is that getting an answer that looks correct isn’t the same as getting an answer that is correct.

And when financial systems are involved, that difference matters.

Because when AI handles people’s money, being almost correct isn’t good enough.

⸻

Built by @haybraham360

Contributions, feedback, and discussions are welcome.