import MySQLdb
from flask import Blueprint, render_template, flash, redirect, url_for, request
from wtforms import Form, StringField, PasswordField, validators
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL


class RegisterForm(Form):
    """
    Form for registering a new user account.
    """

    name = StringField("Name", [validators.Length(min=1, max=50)])
    username = StringField("Username", [validators.Length(min=4, max=25)])
    email = StringField("Email", [validators.Length(min=6, max=50)])
    password = PasswordField(
        "Password",
        [
            validators.DataRequired(),
            validators.EqualTo("confirm", message="Passwords do not match"),
        ],
    )
    confirm = PasswordField("Confirm Password")


def construct_register_form_page(database: MySQL) -> Blueprint:
    """
    Constructs the register form page. This page is used to register a new user.
    :param database: The database object.
    :return: The register form page as a blueprint.
    """
    register_form_page = Blueprint("/register", __name__)

    @register_form_page.route("/register", methods=["GET", "POST"])
    def register() -> str:
        """
        Register a register form page. Connect with the database and 
        create a new user.
        :return: The register form page.
        """

        form = RegisterForm(request.form)

        if request.method == "POST" and form.validate():
            name = form.name.data
            email = form.email.data
            username = form.username.data
            password = sha256_crypt.encrypt(f"{form.password.data}")

            try:

                with database.connection.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO users(name, email, username, password) VALUES('{name}', '{email}', '{username}', '{password}')"
                    )
                    database.connection.commit()

                flash("You are now registered and can log in", "success")
                return redirect(url_for("login"))

            except MySQLdb._exceptions.OperationalError:
                flash("Connection error", "failure")
                return redirect(url_for("login"))

        return render_template("register.html", form=form)

    return register_form_page
