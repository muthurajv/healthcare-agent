"""
Node 5: Human-in-the-loop confirmation before booking.
Uses LangGraph interrupt() to pause the workflow and wait for user slot selection.
"""
from __future__ import annotations

from langgraph.types import interrupt

from agents.state import AppointmentState


def confirm_with_user(state: AppointmentState) -> dict:
    """
    Present available slots to the user and wait for their selection.
    LangGraph interrupt() suspends execution; the graph resumes when the
    caller invokes graph.invoke() again with the user's selection in the state.
    """
    slots = state.get("available_slots", [])
    in_network = state.get("in_network_providers", [])

    if not slots:
        return {
            "response": "I was unable to find available appointment slots matching your criteria. "
                        "Would you like to try different dates or providers?",
            "status": "no_slots_to_confirm",
        }

    # Build a human-readable summary of options (no PHI — provider names are not PHI)
    provider_map = {p["id"]: p for p in in_network}
    slot_summary = []
    for i, slot in enumerate(slots[:5], start=1):
        provider = provider_map.get(slot["provider_id"], {})
        slot_summary.append(
            f"{i}. {provider.get('name', 'Provider')} — "
            f"{slot['date']} at {slot['time']} "
            f"({slot.get('location', '')})"
        )

    confirmation_prompt = (
        "I found the following available appointments:\n\n"
        + "\n".join(slot_summary)
        + "\n\nPlease reply with the number of the slot you'd like to book, or 'cancel' to stop."
    )

    # Suspend and surface the prompt to the user
    user_choice = interrupt({"prompt": confirmation_prompt, "slots": slots})

    # Resume: user_choice contains {"selected_index": int} from the API layer
    selected_index = int(user_choice.get("selected_index", 0))
    if selected_index < 1 or selected_index > len(slots):
        return {
            "response": "Invalid selection. Please try again.",
            "status": "invalid_selection",
        }

    selected = slots[selected_index - 1]
    return {
        "selected_slot": selected,
        "status": "slot_confirmed",
    }
