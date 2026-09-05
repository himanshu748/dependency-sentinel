"""Direct-code deployment entrypoint; AgentCore authenticates inbound calls with IAM."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.agent.runtime_http:app", host="0.0.0.0", port=8080, access_log=False)
