from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services import digital_twin

router = APIRouter(prefix="/twin", tags=["digital twin"])


class SimulateRequest(BaseModel):
    region: str = "Central India"
    load_multiplier: float = Field(3.0, gt=0, le=20)
    replicas: int = Field(1, ge=1, le=20)
    cpu: float | None = None
    latency_ms: float | None = None
    throughput_rps: float | None = None


@router.get("/state")
def twin_state():
    try:
        return digital_twin.read_twin_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate")
def twin_simulate(req: SimulateRequest):
    try:
        return digital_twin.simulate(req.region, req.load_multiplier, req.replicas,
                                     req.cpu, req.latency_ms, req.throughput_rps)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
