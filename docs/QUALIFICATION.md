# Hackathon qualification record

## September 10 release audit

Use [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) for the current required deliverables
and [QWEN-VERIFICATION.md](QWEN-VERIFICATION.md) for the successful real-model checks.
The September 8 table below is historical: Qwen3-8B was subsequently verified through
Strands on September 9, then its Modal endpoint was explicitly stopped. AgentCore
remains unverified. Use [architecture-current.png](architecture-current.png) for the
current provider diagram. Do not attach the older AWS-only architecture as current.

## Historical September 8 review

Checked against the [official rules](https://agentsforhumans.devpost.com/rules), submission fields, dates and judging criteria through the Devpost connector on 2026-09-08 (India time). The official website controls eligibility. Submission closes September 15 at 00:00 UTC / 05:30 IST (September 14, 5 p.m. Pacific).

| Requirement or enhancement | Project evidence | Status |
| --- | --- | --- |
| Strands Agents SDK | Real Agent, tool dispatch and structured output in offline fixture mode; Bedrock provider for live inference | Implemented and locally tested |
| Working end-to-end project | Existing workflow and approval boundary covered by backend/API tests | Local fixture verified |
| Public source, README, MIT/Apache license | Local source, README and Apache-2.0 LICENSE | Latest local revision not verified on the public remote |
| Architecture attachment | [architecture.png](architecture.png), editable [SVG](architecture.svg) | Prepared |
| Public YouTube/Vimeo demo, maximum 5 minutes | [Demo outline](DEMO_SCRIPT.md) | Public video still required |
| AWS Builder ID | Prior work recorded a Builder Center profile | Recheck the actual ID and final submission field |
| New work / disclosure | Solo project; Codex and Claude assisted development. Standard dependencies are declared in lockfiles. | Entrant must confirm any other reused work |
| Optional AgentCore deployment | HTTP contract, packaging and runtime client | Local implementation; current cloud access and end-to-end inference unverified |
| Optional public live demo | Local app currently requires setup | Not publicly hosted |
| Optional Builder Center articles | [Build article draft](BUILDER_POST.md) | Draft only; no bonus earned until public publication |
| Track | Professional Agents | Selected; sponsor determines final fit |

## Required technology versus enhancements

The required framework is Strands Agents SDK. Amazon Bedrock AgentCore is optional and can strengthen the technical score; it is not a separate prize category. Adding unrelated AWS services does not create extra eligibility.

The rules offer 0.2 bonus points per eligible public Builder Center article, capped at 0.6. The title should contain “Agents for Humans.” Each submission needs relevant published content; one project article alone does not establish the maximum bonus for every entry. The final acceptance and score are the judges' decision.

## Deployment evidence and spending boundary

Earlier September 5 checks recorded S3 `NotSignedUp` and a Nova daily-token `ThrottlingException`. Those are historical results, not a fresh diagnosis of current AWS access. No successful cloud invocation or AgentCore deployment is established by this revision's local tests.

Current development remains local with model calls disabled. Use $25 total across all three projects as the conservative current spending ceiling, with the earlier no-bank-charge condition still in place. Credits, budgets, short sessions and token limits are not an account-wide hard billing cap. Do not enable paid inference or deploy under an assumption of guaranteed zero charges. See [activation instructions](ACTIVATION.md) and [bonus evidence plan](BONUS-PLAN.md).

## Local and cloud modes

Fixture mode executes a real Strands Agent using an explicitly scripted model provider. The SDK calls the evidence tool and validates the returned schema. This verifies orchestration without pretending to be LLM inference. Live mode uses Nova directly or sends the advisory request through AgentCore. The local application validates the reply and retains the approval gate and durable writes.

See [AgentCore setup](AGENTCORE.md) for the opt-in implementation. Before claiming submission readiness, verify the latest public source, architecture attachment, public video, AWS Builder ID, actual Devpost record and any bonus article URLs. Separately demonstrate meaningful live Strands/LLM behavior; scripted SDK execution is not evidence that a language model made a useful decision.

## What judges assess

The official criteria are technological implementation, design, potential impact, creativity/originality and presentation. Strands Agents SDK is required. A public live demo and AgentCore can strengthen the technical score but are optional; extra AWS services do not create an automatic bonus. Demonstrate a complete workflow, a saved result and a visible human decision, not only a landing page or a successful HTTP response.
