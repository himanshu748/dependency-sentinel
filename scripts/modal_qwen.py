"""Private, scale-to-zero Qwen endpoint shared by the three hackathon products.

Deploy once from one checkout after confirming Modal credit coverage and the workspace
usage cap. Do not deploy three separate model servers.
"""

import subprocess

import modal

MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
APP_NAME = "agents-for-humans-qwen"

image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm==0.21.0")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)
cache = modal.Volume.from_name("agents-for-humans-qwen-cache", create_if_missing=True)
app = modal.App(APP_NAME)


def server_command() -> list[str]:
    return [
        "vllm",
        "serve",
        MODEL_ID,
        "--revision",
        MODEL_REVISION,
        "--served-model-name",
        MODEL_ID,
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--dtype",
        "half",
        "--max-model-len",
        "8192",
        "--max-num-seqs",
        "2",
        "--gpu-memory-utilization",
        "0.90",
        "--enforce-eager",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "hermes",
        "--default-chat-template-kwargs",
        '{"enable_thinking": false}',
    ]


@app.server(
    image=image,
    gpu="L4",
    cpu=2,
    memory=8192,
    min_containers=0,
    max_containers=1,
    buffer_containers=0,
    target_concurrency=2,
    scaledown_window=120,
    startup_timeout=600,
    volumes={"/root/.cache/huggingface": cache},
    port=8000,
    routing_region="us-east",
    unauthenticated=False,
)
class QwenServer:
    @modal.enter()
    def start(self):
        self.process = subprocess.Popen(server_command())

    @modal.exit()
    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
