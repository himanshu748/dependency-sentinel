# Dependency Sentinel demo video outline

Status: recording and public upload pending. The final video must be public on YouTube or Vimeo and at most five minutes.

Recording update, September 10: real Qwen3-8B tool workflows were verified on Modal
on September 9. The endpoint is deliberately stopped. Resume it only with approval,
warm it, and record fresh execution. When recording Qwen, identify Qwen + Strands
accurately rather than reading any older fixture-only narration below. When using
the free scripted demo, label it scripted throughout. Use architecture-current.png.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:25 | Product landing page | Who the product helps and the repeated task they face |
| 0:25–0:50 | Controlled local fixture + trust checkbox | Show a clean committed repository. Tests execute locally; a worktree is not a security sandbox. State that this run uses fixture advisory data and a scripted model. |
| 0:50–1:45 | Run the application and inspect evidence | Verify candidate; stage + validate in worktree; show where the source evidence comes from |
| 1:45–2:30 | Passing checks, exact source SHA, then approve | No download before approval. Explain that approval records the reviewed result and does not apply the patch. |
| 2:30–3:15 | Download patch and review receipt | Open the JSON receipt: captured commit, evidence retrieval times, exact commands/results, approval time, execution mode and patch SHA-256. The receipt checks local consistency; it is not a signed attestation. |
| 3:15–3:45 | Architecture PNG + Strands code | Name Strands Agents SDK; distinguish scripted demo from live inference |
| 3:45–4:15 | Reopen approved run; show failed-run boundary | Source remains unchanged. A failed, incomplete or legacy unbound record cannot export. The fixture validates staged metadata; live mode resolves and tests the locked environment separately. |

Do not show an AgentCore deployment or live Nova response until one has been verified. Mention Codex and Claude as development assistants. Keep AWS console credentials, account tokens, personal data and private browser tabs out of the recording.

Required publication: attach the public YouTube/Vimeo URL to the Devpost project, then watch the entire uploaded video to verify audio/text readability and duration.
