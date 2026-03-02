"""Ideas API — CRUD for video ideas."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.idea import Idea

ideas_bp = Blueprint("ideas", __name__)


@ideas_bp.route("/", methods=["GET"])
def list_ideas():
    channel_id = request.args.get("channel_id")
    status = request.args.get("status")
    query = Idea.query.order_by(Idea.created_at.desc())
    if channel_id:
        query = query.filter_by(channel_id=channel_id)
    if status:
        query = query.filter_by(status=status)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        "ideas": [i.to_dict() for i in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@ideas_bp.route("/<idea_id>", methods=["GET"])
def get_idea(idea_id):
    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({"error": "Idea not found"}), 404
    return jsonify(idea.to_dict())


@ideas_bp.route("/", methods=["POST"])
def create_idea():
    data = request.get_json()
    if not data or not data.get("channel_id") or not data.get("topic"):
        return jsonify({"error": "channel_id and topic are required"}), 400

    idea = Idea(
        channel_id=data["channel_id"],
        topic=data["topic"],
        score=data.get("score"),
        source=data.get("source", "manual"),
        status=data.get("status", "pending"),
        meta_json=data.get("meta_json", {}),
    )
    db.session.add(idea)
    db.session.commit()
    return jsonify(idea.to_dict()), 201


@ideas_bp.route("/<idea_id>", methods=["PATCH"])
def update_idea(idea_id):
    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({"error": "Idea not found"}), 404

    data = request.get_json() or {}
    for field in ["topic", "score", "source", "status", "meta_json"]:
        if field in data:
            setattr(idea, field, data[field])

    db.session.commit()
    return jsonify(idea.to_dict())


@ideas_bp.route("/<idea_id>", methods=["DELETE"])
def delete_idea(idea_id):
    idea = Idea.query.get(idea_id)
    if not idea:
        return jsonify({"error": "Idea not found"}), 404

    db.session.delete(idea)
    db.session.commit()
    return jsonify({"message": "Idea deleted"})
