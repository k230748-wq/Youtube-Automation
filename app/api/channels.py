"""Channels API — CRUD for YouTube channels."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.channel import Channel

channels_bp = Blueprint("channels", __name__)


@channels_bp.route("/", methods=["GET"])
def list_channels():
    channels = Channel.query.order_by(Channel.created_at.desc()).all()
    return jsonify({"channels": [c.to_dict() for c in channels]})


@channels_bp.route("/", methods=["POST"])
def create_channel():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("niche"):
        return jsonify({"error": "name and niche are required"}), 400

    channel = Channel(
        name=data["name"],
        niche=data["niche"],
        youtube_channel_id=data.get("youtube_channel_id"),
        voice_id=data.get("voice_id"),
        language=data.get("language", "en"),
        config=data.get("config", {}),
    )
    db.session.add(channel)
    db.session.commit()
    return jsonify(channel.to_dict()), 201


@channels_bp.route("/<channel_id>", methods=["GET"])
def get_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    return jsonify(channel.to_dict())


@channels_bp.route("/<channel_id>", methods=["PATCH"])
def update_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404

    data = request.get_json() or {}
    for field in ["name", "niche", "youtube_channel_id", "voice_id", "language", "active", "config"]:
        if field in data:
            setattr(channel, field, data[field])

    db.session.commit()
    return jsonify(channel.to_dict())


@channels_bp.route("/<channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    channel.active = False
    db.session.commit()
    return jsonify({"message": "Channel deactivated"})
