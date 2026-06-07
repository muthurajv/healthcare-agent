"""
POST /appointments/request  — starts a new appointment search workflow
POST /appointments/confirm  — resumes the workflow after user slot selection
GET  /appointments/{thread_id}/status — check workflow state
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.workflow import appointment_graph

router = APIRouter(prefix="/appointments", tags=["appointments"])


class AppointmentRequest(BaseModel):
    user_request: str
    user_id: str
    member_id_token: str | None = None
    insurance_plan: str | None = None


class SlotConfirmation(BaseModel):
    thread_id: str
    selected_index: int


class AppointmentResponse(BaseModel):
    thread_id: str
    status: str
    response: str | None = None
    available_slots: list[dict] | None = None
    appointment_id: str | None = None
    awaiting_confirmation: bool = False


@router.post("/request", response_model=AppointmentResponse)
async def request_appointment(body: AppointmentRequest) -> AppointmentResponse:
    """
    Start the appointment-finding workflow.
    Returns immediately if the workflow reaches the human-confirmation interrupt,
    surfacing available slots for the user to choose from.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "user_request": body.user_request,
        "user_id": body.user_id,
        "member_id_token": body.member_id_token or "",
        "insurance_plan": body.insurance_plan or "",
        "status": "started",
    }

    # Run until the first interrupt (confirm_with_user) or completion
    result = appointment_graph.invoke(initial_state, config=config)

    awaiting = result.get("status") not in (
        "scheduled", "no_providers_found", "no_in_network_providers",
        "no_slots_found", "consent_denied", "scheduling_failed",
    ) and result.get("available_slots")

    return AppointmentResponse(
        thread_id=thread_id,
        status=result.get("status", "unknown"),
        response=result.get("response"),
        available_slots=result.get("available_slots") if awaiting else None,
        appointment_id=result.get("appointment_id"),
        awaiting_confirmation=bool(awaiting),
    )


@router.post("/confirm", response_model=AppointmentResponse)
async def confirm_appointment(body: SlotConfirmation) -> AppointmentResponse:
    """
    Resume the workflow after the user selects an appointment slot.
    """
    config = {"configurable": {"thread_id": body.thread_id}}

    # Resume with user's choice — LangGraph reads from checkpoint then continues
    result = appointment_graph.invoke(
        {"selected_index": body.selected_index},
        config=config,
    )

    return AppointmentResponse(
        thread_id=body.thread_id,
        status=result.get("status", "unknown"),
        response=result.get("response"),
        appointment_id=result.get("appointment_id"),
        awaiting_confirmation=False,
    )


@router.get("/{thread_id}/status", response_model=AppointmentResponse)
async def get_status(thread_id: str) -> AppointmentResponse:
    """Return current state of a workflow thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = appointment_graph.get_state(config)
    except Exception:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = snapshot.values if snapshot else {}
    return AppointmentResponse(
        thread_id=thread_id,
        status=state.get("status", "unknown"),
        response=state.get("response"),
        appointment_id=state.get("appointment_id"),
        awaiting_confirmation=bool(state.get("available_slots") and not state.get("appointment_id")),
    )
