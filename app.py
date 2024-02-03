from flask import flash, Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from fractions import Fraction

app = Flask(__name__)
# creating URI to access
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'oOeSDJ3nyrthKs1' 
# creating my db with the app
db = SQLAlchemy(app)

# creating schema for Recipe
class Recipe(db.Model):
    # primary key identifier
    recipe_id = db.Column(db.Integer, primary_key=True)
    # name to be input
    name = db.Column(db.String(255), nullable=False)
    # description for reference
    description = db.Column(db.Text, nullable=True)
    # recipe steps // don't love the storage of this but simple application 
    steps = db.Column(db.Text, nullable=False)
    recipe_type = db.Column(db.String(20), nullable=False)
    mood_id = db.Column(db.String(20), db.ForeignKey('mood.mood_id'), nullable=True)
    # mood = db.relationship('Mood', backref='recipes', lazy=True)
    servings = db.Column(db.Integer, nullable=False)

# creating Recipe Ingredient table to match to recipes, ingredients, quantities, and units
class RecipeIngredient(db.Model):
    # primary key 
    recipe_ingredient_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.recipe_id'), nullable=False)
    measurement_id = db.Column(db.Integer, db.ForeignKey('measurement_units.measurement_id'), nullable=False)
    measurement_qty_id = db.Column(db.Integer, db.ForeignKey('measurement_qty.measurement_qty_id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.ingredient_id'), nullable=False)
    recipe = db.relationship('Recipe', backref=db.backref('recipe_ingredients', lazy=True))
    measurement_units = db.relationship('MeasurementUnits', backref=db.backref('recipe_ingredients', lazy=True))
    measurement_qty = db.relationship('MeasurementQty', backref=db.backref('recipe_ingredients', lazy=True))
    ingredient = db.relationship('Ingredients', backref=db.backref('recipe_ingredients', lazy=True))

# creating measurement units table to store units
class MeasurementUnits(db.Model):
    measurement_id = db.Column(db.Integer, primary_key=True)
    measurement_description = db.Column(db.String(50), nullable=False)

# creating measurement qty table to store quantities
class MeasurementQty(db.Model):
    # primary key
    measurement_qty_id = db.Column(db.Integer, primary_key=True)
    qty_amount = db.Column(db.Numeric(4, 3), nullable=False)

# creating an Ingredients table
class Ingredients(db.Model):
    # primary key
    ingredient_id = db.Column(db.Integer, primary_key=True)
    # to be input
    ingredient_name = db.Column(db.String(255), nullable=False)

class Mood(db.Model):
    # primary key 
    mood_id = db.Column(db.Integer, primary_key=True)
    mood = db.Column(db.String(20), nullable=False)

# create all tables in the sql database
with app.app_context():
    db.create_all()


# adding predefined moods (subject to add more)
def add_predefined_moods():
    predefined_moods = ['Hearty', 'Light', 'Romantic', 'Period Cravings', 'Healthy', 'Comforting', 'Spicy', 'Easy', 'Clean']

    for mood_name in predefined_moods:
        mood_obj = Mood.query.filter_by(mood=mood_name).first()

        if not mood_obj:
            mood_obj = Mood(mood=mood_name)
            db.session.add(mood_obj)

    db.session.commit()

# run the function to add predefined moods to the database
with app.app_context():
    add_predefined_moods()

# getting all stored recipes
@app.route('/recipes', methods=['GET'])
def get_recipes():
    recipes = Recipe.query.all()
    
    # matching schema above
    recipe_list = [
        {
            'recipe_id': recipe.recipe_id,
            'name': recipe.name,
            'description': recipe.description,
            'steps': recipe.steps.split('\n') if recipe.steps else [],
            'ingredients': get_recipe_ingredients(recipe.recipe_id),
            'recipe_type': recipe.recipe_type,
            'mood': get_mood(recipe.mood_id),
            'servings': recipe.servings
        }
        for recipe in recipes
    ]

    # returning as a JSON object for readability
    return jsonify(recipe_list)

# get mood function associated to get mood above for recipe
def get_mood(mood_id):
    mood = db.session.query(Mood.mood).filter(Mood.mood_id == mood_id).first()
    return mood.mood if mood else None

# function called above to fetch recipe ingredients for a recipe
def get_recipe_ingredients(recipe_id):
    ingredients = (
        db.session.query(
            Ingredients.ingredient_name,
            MeasurementQty.qty_amount,
            MeasurementUnits.measurement_description
        )
        .join(RecipeIngredient, Ingredients.ingredient_id == RecipeIngredient.ingredient_id)
        .join(MeasurementQty, RecipeIngredient.measurement_qty_id == MeasurementQty.measurement_qty_id)
        .join(MeasurementUnits, RecipeIngredient.measurement_id == MeasurementUnits.measurement_id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )

    return [
        {
            'name': ingredient.ingredient_name,
            'quantity': f"{ingredient.qty_amount} {ingredient.measurement_description}"
        }
        for ingredient in ingredients
    ]


# new page to add a recipe with a form in the templates folder
@app.route('/add_recipe', methods=['GET'])
def add_recipe_page():
    return render_template('add_recipe.html') 

# same route but for handling the form submission
@app.route('/add_recipe', methods=['POST'])
def add_recipe():
    try: 
        ########## Adding input recipe to Recipe database ##########
        # process and store the recipe in the database
        name = request.form.get('name')
        description = request.form.get('description')
        steps = request.form.getlist('steps[]')
        recipe_type = request.form.get('recipe_type')
        mood = request.form.get('mood')
        mood_id = Mood.query.get(mood).mood_id
        servings = request.form.get('servings')

        # Print the form inputs for debugging
        print(f"Name: {name}, Description: {description}, Steps: {steps}, Recipe Type: {recipe_type}, Mood ID: {mood_id}, Servings: {servings}")

        # creating new recipe object from the field information entered above
        ## ------------- Do we need to parse/clean this data? 
        new_recipe = Recipe(name=name, description=description, steps='\n'.join(steps), recipe_type=recipe_type, mood_id=mood_id, servings=servings)

        # Print the new recipe details for debugging
        print(f"New Recipe: {new_recipe}")

        # adding the new recipe to the database
        db.session.add(new_recipe)
        db.session.commit()

        # Print a success message for debugging
        print("Recipe added successfully!")

        ########## Getting the dynamic field information ##########
        ########## Ingredients, MeasurementQty, RecipeIngredient, MeasurementUnits tables ##########
        
        # handling the dynamic ingredient fields as lists
        ingredients = request.form.getlist('ingredients[]')
        quantities = request.form.getlist('quantities[]')
        units = request.form.getlist('units[]')

        # creating a zip of lists to deal with each value individually
        for ingredient, quantity, unit in zip(ingredients, quantities, units):
            # these will add primary keys on their own, incremental
            ingredient_obj = Ingredients.query.filter_by(ingredient_name=ingredient).first()
            measurement_qty_obj = MeasurementQty.query.filter_by(qty_amount=quantity).first()
            measurement_units_obj = MeasurementUnits.query.filter_by(measurement_description=unit).first()

        # check if ingredient, quantity, and unit exist in the database
            # if doesn't exist, add as an Ingredient object
            if not ingredient_obj:
                ingredient_obj = Ingredients(ingredient_name=ingredient)
                db.session.add(ingredient_obj)
            # if doesn't exist, add as a MeasurementQty object
            if not measurement_qty_obj:
                try:
                    quantity=float(quantity)
                except ValueError:
                    try:
                        quantity=Fraction(quantity)
                    except:
                        flash(f'Invalid quantity: {quantity}. Please enter a valid fraction or decimal.', 'error')
                measurement_qty_obj = MeasurementQty(qty_amount=float(quantity))
                db.session.add(measurement_qty_obj)
            # if doesn't exist, add as a MeasurementUnits object
            if not measurement_units_obj:
                measurement_units_obj = MeasurementUnits(measurement_description=unit)
                db.session.add(measurement_units_obj)

            ########## Concatenating all of the information together per ingredient added ##########
            recipe_ingredient = RecipeIngredient(
                recipe=new_recipe,
                ingredient=ingredient_obj,
                measurement_qty=measurement_qty_obj,
                measurement_units=measurement_units_obj
            )
            ### Adding to the recipe ingredient table
            db.session.add(recipe_ingredient)

        # commit all changes to the database
        db.session.commit()

        # redirect to the recipe detail page after adding
        return redirect(url_for('get_recipe_details', recipe_id=new_recipe.recipe_id))
    
    except Exception as e:
        # Print the error for debugging
        print(f"Error: {str(e)}")
       # handle the exception, log it, and provide an error message to the user
        db.session.rollback()
        flash(f'Error adding recipe: {str(e)}', 'error')
        return redirect(url_for('add_recipe'))

# running the app
if __name__ == '__main__':
    app.run(debug=True)
