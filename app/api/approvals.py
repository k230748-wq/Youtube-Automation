"""Approvals API — human-in-the-loop approval management."""

from flask import Blueprint, request, jsonify

from app.models.approval import Approval
from app.models.phase_result import PhaseResult
from app.orchestrator.gates import resolve_approval

approvals_bp = Blueprint("approvals", __name__)


@approvals_bp.route("/pending", methods=["GET"])
def list_pending():
    """List all pending approvals."""
    approvals = Approval.query.filter_by(status="pending").order_by(
        Approval.created_at.desc()
    ).all()

    results = []
    for a in approvals:
        phase_result = PhaseResult.query.get(a.phase_result_id)
        results.append({
            **a.to_dict(),
            "phase_output": phase_result.output_data if phase_result else None,
            "phase_name": phase_result.agent_name if phase_result else None,
        })

    return jsonify({"approvals": results})


@approvals_bp.route("/<approval_id>", methods=["GET"])
def get_approval(approval_id):
    """Get a single approval with full phase output."""
    approval = Approval.query.get(approval_id)
    if not approval:
        return jsonify({"error": "Approval not found"}), 404

    phase_result = PhaseResult.query.get(approval.phase_result_id)

    return jsonify({
        **approval.to_dict(),
        "phase_output": phase_result.output_data if phase_result else None,
        "phase_input": phase_result.input_data if phase_result else None,
        "prompt_used": phase_result.prompt_used if phase_result else None,
    })


@approvals_bp.route("/<approval_id>/resolve", methods=["POST"])
def resolve(approval_id):
    """Approve, reject, or edit a phase output."""
    data = request.get_json()

    decision = data.get("decision")  # approved | rejected | edited
    if decision not in ("approved", "rejected", "edited"):
        return jsonify({"error": "decision must be 'approved', 'rejected', or 'edited'"}), 400

    notes = data.get("notes")
    edited_output = data.get("edited_output")

    try:
        approval = resolve_approval(
            approval_id=approval_id,
            decision=decision,
            notes=notes,
            edited_output=edited_output,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # If approved or edited, resume the pipeline
    if decision in ("approved", "edited"):
        from worker.tasks import resume_after_approval
        resume_after_approval.delay(approval.pipeline_run_id, approval.phase_number)

    return jsonify({
        "message": f"Phase {approval.phase_number} {decision}",
        "approval": approval.to_dict(),
    })
