from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    return render_template("index.html")


@public_bp.route("/about")
def about():

    about = {
        "title": "About Fortune Needles",
        "subtitle": "Crafting elegance through custom tailoring.",
        "who_we_are": "Fortune Needles is a modern tailoring brand..."
    }

    return render_template(
        "about.html",
        about=about
    )


@public_bp.route("/services")
def services():
    return render_template("services.html")


@public_bp.route("/gallery")
def gallery():
    return render_template("gallery.html")


@public_bp.route("/shop")
def shop():
    return render_template("shop.html")


@public_bp.route("/contact")
def contact():
    return render_template("contact.html")