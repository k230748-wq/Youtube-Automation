"""Seed the database with default data."""

from app import create_app, db
from app.models.phase_toggle import PhaseToggle
from app.models.channel import Channel


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        PhaseToggle.seed_defaults(db.session)
        print("Database seeded successfully.")


if __name__ == "__main__":
    seed()
