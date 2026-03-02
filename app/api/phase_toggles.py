"""Phase Toggles API — enable/disable phases, configure approval gates."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.phase_toggle import PhaseToggle

toggles_bp = Blueprint("toggles", __name__)


@toggles_bp.route("/", methods=["GET"])
def list_toggles():
    toggles = PhaseToggle.query.order_by(PhaseToggle.phase_number).all()
    return jsonify({"toggles": [t.to_dict() for t in toggles]})


@toggles_bp.route("/<int:phase_number>", methods=["PATCH"])
def update_toggle(phase_number):
    toggle = PhaseToggle.query.filter_by(phase_number=phase_number).first()
    if not toggle:
        return jsonify({"error": f"Phase {phase_number} toggle not found"}), 404

    data = request.get_json() or {}
    if "is_enabled" in data:
        toggle.is_enabled = data["is_enabled"]
    if "requires_approval" in data:
        toggle.requires_approval = data["requires_approval"]

    db.session.commit()
    return jsonify(toggle.to_dict())


@toggles_bp.route("/seed", methods=["POST"])
def seed_toggles():
    """Seed default phase toggles if they don't exist."""
    PhaseToggle.seed_defaults(db.session)
    toggles = PhaseToggle.query.order_by(PhaseToggle.phase_number).all()
    return jsonify({"message": "Seeded", "toggles": [t.to_dict() for t in toggles]})
