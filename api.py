from fastapi import FastAPI
from pydantic import BaseModel, Field
from app.discovery.engine import RequirementDiscoveryEngine
from app.discovery.confirmation import ConfirmationGate
from app.models.schemas import DiscoveryResult

app = FastAPI(title="AI Agency Requirement Discovery API", version="0.2.0")
engine = RequirementDiscoveryEngine()
gate = ConfirmationGate()

class DiscoveryRequest(BaseModel):
    prompt: str = Field(min_length=1)
    references: list[str] = []

class ConfirmationRequest(BaseModel):
    result: DiscoveryResult
    key: str
    value: str | bool | int | float | list[str]

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2"}

@app.post("/discover", response_model=DiscoveryResult)
def discover(payload: DiscoveryRequest):
    return engine.analyze(payload.prompt, payload.references)

@app.post("/confirm", response_model=DiscoveryResult)
def confirm(payload: ConfirmationRequest):
    return gate.promote_confirmed(payload.result, payload.key, payload.value)
