"""Assets API — list and manage video assets."""

from flask import Blueprint, request, jsonify

from app import db
from app.models.asset import Asset

assets_bp = Blueprint("assets", __name__)


@assets_bp.route("/", methods=["GET"])
def list_assets():
    video_id = request.args.get("video_id")
    asset_type = request.args.get("type")
    query = Asset.query.order_by(Asset.created_at.desc())
    if video_id:
        query = query.filter_by(video_id=video_id)
    if asset_type:
        query = query.filter_by(type=asset_type)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        "assets": [a.to_dict() for a in pagination.items],
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages,
    })


@assets_bp.route("/<asset_id>", methods=["GET"])
def get_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404
    return jsonify(asset.to_dict())


@assets_bp.route("/<asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({"error": "Asset not found"}), 404

    # Delete file from disk if it exists
    if asset.file_path:
        import os
        if os.path.exists(asset.file_path):
            os.remove(asset.file_path)

    db.session.delete(asset)
    db.session.commit()
    return jsonify({"message": "Asset deleted"})
