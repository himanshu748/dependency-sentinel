# Bonus and submission evidence plan

September 10 status: the real Qwen workflow passed on September 9; see
[QWEN-VERIFICATION.md](QWEN-VERIFICATION.md). The model endpoint is now stopped by
request. The publication gates in [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) remain
open. No article bonus or AgentCore deployment is claimed.

Checked through the official Devpost connector on September 9, 2026
(rules, judging criteria, prize list, submission requirements and announcements).
Source: [Agents for Humans](https://agentsforhumans.devpost.com/rules).

Dependency Sentinel targets **Professional Agents**. The three entry tracks have prize tiers; there are no
additional sponsor-technology prize categories in the fetched prize list.

| Opportunity | Preparation | Remaining proof |
| --- | --- | --- |
| Required meaningful Strands workflow | SDK, read-only tools, typed output, deterministic validation and approval | Demonstrate a real model handling a fresh input end-to-end |
| AgentCore technical-score enhancement | ARM64 packaging, IAM runtime client, configuration launcher | Deploy and record READY plus a successful real advisory call |
| Live-demo technical-score enhancement | Local product UI and API | Safe hosting, authentication, authorization, rate limits and judge access |
| Builder Center article bonus | Existing build-journey draft | Public URLs before the deadline; link relevant articles to this entry |
| Public source and architecture | Repository files and architecture assets | Verify latest public commit, license and diagram against recorded demo |
| Public video, maximum five minutes | Existing demo script | Record genuine execution and verify public playback |

## Maximum article bonus target

The rules specify 0.2 per eligible public contribution, capped at 0.6 in Stage Two.
Three relevant posts are the target, not a guarantee of award. Do not assume one
generic post earns the maximum for all three projects. Include “Agents for Humans”
in every title. The August 12 update removed the hashtag requirement.

Prepare this distinct series for Dependency Sentinel:

1. Build journey: revise [BUILDER_POST.md](BUILDER_POST.md) against actual verification.
2. Agents for Humans: Keeping repository execution outside the cloud agent.
3. Agents for Humans: What an upgrade receipt proves, and what passing tests do not.

For posts 2 and 3, include the concrete code boundary, one tested failure case, one
workflow screenshot and a link to the repository. Distinguish implemented local
behavior from cloud behavior that has actually been verified. These are editorial
briefs, not published articles. No new blog has been published by this preparation.

## Evidence checklist

- [ ] Fresh real-model workflow succeeds; model and tool usage recorded without secrets.
- [ ] AgentCore runtime and DEFAULT endpoint READY, invocation and session stop captured.
- [ ] Public demo safely accessible, or reproducible test build with honest access limits.
- [ ] Three relevant Builder Center posts publicly published and URLs added to Devpost.
- [ ] Public source includes current code, assets, setup and MIT/Apache license.
- [ ] Video shows input, useful agent work, approval and result; no mocked success claims.
- [ ] Actual AWS Builder ID and latest Devpost submission receipt verified.


Adding unrelated AWS services consumes time and may add cost without earning points.
Complete the core workflow before pursuing hosting or additional articles.
