#!/usr/bin/env python3
import os
from flask import Flask, request
from flask_migrate import Migrate
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError
from models import db, Restaurant, RestaurantPizza, Pizza

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

migrate = Migrate(app, db)
db.init_app(app)
api = Api(app)


@app.route("/")
def index():
    return "<h1>Code challenge</h1>"


class Restaurants(Resource):
    def get(self):
        restaurants = Restaurant.query.all()
        return [r.to_dict(only=("id", "name", "address")) for r in restaurants], 200


class RestaurantByID(Resource):
    def get(self, id):
        restaurant = db.session.get(Restaurant, id)
        if not restaurant:
            return {"error": "Restaurant not found"}, 404

        data = restaurant.to_dict(only=("id", "name", "address"))
        data["restaurant_pizzas"] = [
            {
                **rp.to_dict(
                    only=("id", "price", "pizza_id", "restaurant_id"),
                    rules=("-pizza.restaurant_pizzas",)
                ),
                "pizza": rp.pizza.to_dict(only=("id", "name", "ingredients")),
            }
            for rp in restaurant.restaurant_pizzas
        ]
        return data, 200

    def delete(self, id):
        restaurant = db.session.get(Restaurant, id)
        if not restaurant:
            return {"error": "Restaurant not found"}, 404

        db.session.delete(restaurant)
        db.session.commit()
        return "", 204


class Pizzas(Resource):
    def get(self):
        pizzas = Pizza.query.all()
        return [p.to_dict(only=("id", "name", "ingredients")) for p in pizzas], 200

    def post(self):
        data = request.get_json()
        try:
            new_pizza = Pizza(
                name=data.get("name"),
                ingredients=data.get("ingredients"),
            )
            db.session.add(new_pizza)
            db.session.commit()

            return new_pizza.to_dict(only=("id", "name", "ingredients")), 201

        except Exception as e:
            db.session.rollback()
            return {"errors": [str(e)]}, 400


class RestaurantPizzas(Resource):
    def post(self):
        data = request.get_json()

        try:
            new_rp = RestaurantPizza(
                price=data.get("price"),
                pizza_id=data.get("pizza_id"),
                restaurant_id=data.get("restaurant_id"),
            )
            db.session.add(new_rp)
            db.session.commit()

            db.session.refresh(new_rp)

            return {
                **new_rp.to_dict(
                    only=("id", "price", "pizza_id", "restaurant_id"),
                    rules=("-pizza.restaurant_pizzas", "-restaurant.restaurant_pizzas"),
                ),
                "pizza": new_rp.pizza.to_dict(only=("id", "name", "ingredients")),
                "restaurant": new_rp.restaurant.to_dict(only=("id", "name", "address")),
            }, 201

        except (ValueError, IntegrityError):
            db.session.rollback()
            return {"errors": ["validation errors"]}, 400


api.add_resource(Restaurants, "/restaurants")
api.add_resource(RestaurantByID, "/restaurants/<int:id>")
api.add_resource(Pizzas, "/pizzas")
api.add_resource(RestaurantPizzas, "/restaurant_pizzas")


if __name__ == "__main__":
    app.run(port=5555, debug=True)