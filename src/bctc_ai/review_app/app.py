"""Flask application factory for the BCTC mapping review workspace."""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, request, send_file

from .federated import build_review_repository
from .repository import ReviewSettings


def create_app(settings: ReviewSettings | None = None) -> Flask:
    """Create a configured read-only review application."""

    app = Flask(__name__)
    repository = build_review_repository(settings or ReviewSettings.from_environment())
    app.extensions["bctc_review_repository"] = repository

    @app.get("/")
    def index():
        return render_template(
            "review_app/index.html", configuration=repository.configuration_status()
        )

    @app.get("/healthz")
    def health():
        status = repository.configuration_status()
        return jsonify(status), 200 if status["ready"] else 503

    @app.get("/api/options")
    def options():
        return jsonify(repository.options())

    @app.get("/api/documents")
    def documents():
        family_id = request.args.get("family_id", "").strip()
        if not family_id:
            return jsonify({"error": "Thiếu family_id"}), 400
        filters = {
            key: request.args.get(key, "").strip()
            for key in ("bank", "year", "period", "scope", "assurance", "status", "query")
        }
        return jsonify({"documents": repository.documents(family_id, filters)})

    @app.get("/api/review/<family_id>/<source_sha256>")
    def review(family_id: str, source_sha256: str):
        return jsonify(repository.review(family_id, source_sha256))

    @app.get("/api/page-image/<source_sha256>/<int:physical_page>")
    def page_image(source_sha256: str, physical_page: int):
        path = repository.render_page(source_sha256, physical_page)
        return send_file(path, mimetype="image/png", conditional=True, max_age=86400)

    @app.errorhandler(FileNotFoundError)
    @app.errorhandler(LookupError)
    def not_found(error: Exception):
        return jsonify({"error": str(error)}), 404

    @app.errorhandler(ValueError)
    def invalid(error: ValueError):
        return jsonify({"error": str(error)}), 400

    return app


def main() -> None:
    """Run the development review server using environment configuration."""

    app = create_app()
    host = os.environ.get("BCTC_REVIEW_HOST", "0.0.0.0")
    port = int(os.environ.get("BCTC_REVIEW_PORT", "8000"))
    debug = os.environ.get("BCTC_REVIEW_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
