from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import func

from extensions import db
from models import Review
from routes.admin import admin_bp, section_required


@admin_bp.route("/reviews")
@section_required("shop")
def admin_reviews():

    rating = request.args.get("rating", type=int)

    query = Review.query

    if rating in range(1, 6):
        query = query.filter(Review.rating == rating)

    counts = dict(db.session.query(Review.rating, func.count(Review.id)).group_by(Review.rating).all())
    average = db.session.query(func.avg(Review.rating)).scalar()

    return render_template(
        "admin/reviews.html",
        reviews=query.order_by(Review.created_at.desc()).all(),
        rating=rating,
        counts=counts,
        total=sum(counts.values()),
        average=average
    )


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@section_required("shop")
def delete_review(review_id):

    review = db.get_or_404(Review, review_id)

    db.session.delete(review)
    db.session.commit()

    flash("Review deleted.", "success")

    return redirect(request.referrer or url_for("admin.admin_reviews"))
