# Hackathon qualification record

Checked against the [official rules](https://agentsforhumans.devpost.com/rules), submission fields, judging criteria and prizes through the Devpost connector on 2026-09-05. The official website controls eligibility.

| Requirement or enhancement | Project evidence | Status |
| --- | --- | --- |
| Strands Agents SDK | Real Agent, tool dispatch and structured output in offline fixture mode; Bedrock provider for live inference | Implemented and locally tested |
| Working end-to-end project | Existing workflow and approval boundary covered by backend/API tests | Local fixture verified |
| Public source, README, MIT/Apache license | This public repository and Apache-2.0 LICENSE | Present |
| Architecture attachment | [architecture.png](architecture.png), editable [SVG](architecture.svg) | Prepared |
| Public YouTube/Vimeo demo, maximum 5 minutes | [Demo outline](DEMO_SCRIPT.md) | Public video still required |
| AWS Builder ID | Public Builder Center profile @jhahimanshu653 verified | Final Devpost field still required |
| New work / disclosure | Solo project; Codex and Claude assisted development. Standard dependencies are declared in lockfiles. | Entrant must confirm any other reused work |
| Optional AgentCore deployment | HTTP contract, scoped IAM role, ARM64 zip packaging, runtime client | Implemented; AWS account blocks live deployment |
| Optional public live demo | Local app currently requires setup | Not publicly hosted |
| Optional Builder Center articles | [Build article draft](BUILDER_POST.md) | Draft only; no bonus earned until public publication |
| Track | Professional Agents | Selected; sponsor determines final fit |

## Required technology versus enhancements

The required framework is Strands Agents SDK. Amazon Bedrock AgentCore is optional and can strengthen the technical score; it is not a separate prize category. Adding unrelated AWS services does not create extra eligibility.

The rules offer 0.2 bonus points per eligible public Builder Center article, capped at 0.6. The title should contain “Agents for Humans.” Each submission needs relevant published content; one project article alone does not establish the maximum bonus for every entry. The final acceptance and score are the judges' decision.

## Current deployment evidence

The AWS CLI authenticated successfully. The attempted private S3 deployment failed with `NotSignedUp`; no runtime, role or deployment bucket was created. A minimal Nova invocation returned a daily-token `ThrottlingException`. The alternative saved project login had expired. No successful cloud invocation or AgentCore deployment is claimed.

The user authorized a combined $5 deployment/test limit for all three projects. The deployment script creates no continuously provisioned instances. Each runtime invocation has a model-call ceiling, 512 output tokens per model request, a five-minute maximum session lifetime, and explicit session stop in the client. These controls bound this workflow, but are not an account-wide billing hard cap.

## Local and cloud modes

Fixture mode executes a real Strands Agent using an explicitly scripted model provider. The SDK calls the evidence tool and validates the returned schema. This verifies orchestration without pretending to be LLM inference. Live mode uses Nova directly or sends the advisory request through AgentCore. The local application validates the reply and retains the approval gate and durable writes.

See [AgentCore setup](AGENTCORE.md) for deployment and test commands. Do not mark the project fully qualified until the public video, AWS Builder ID, Devpost submission, and any claimed bonus article URLs are verified.
