import streamlit as st
import json
import os
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
import time
import requests 
import re 

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.exceptions import OutputParserException 

# --- 1. Pydantic Schemas ---

class Ingredient(BaseModel):
    item: str = Field(description="The name of the ingredient.")
    quantity: str = Field(description="The precise amount needed, e.g., '1 cup', '2 tablespoons', '500g'.")

class Recipe(BaseModel):
    """A structured representation of a complete cooking recipe."""
    name: str = Field(description="The engaging and descriptive title of the recipe.")
    description: str = Field(description="A brief, appetizing summary (1-2 sentences) of the final dish.")
    category: str = Field(description="The meal category, e.g., 'Main Course', 'Dessert', 'Appetizer'.")
    nutritional_tip: str = Field(description="A short, relevant health or nutritional tip for this recipe.")
    historical_fact: str = Field(description="A single, interesting historical or origin fact (1-2 sentences) about this dish or its main ingredients.")
    total_calories_kcal: int = Field(description="The estimated total caloric content (kcal) *per serving* of this dish. Must be an integer.")
    prep_time_minutes: int = Field(description="The estimated total preparation and cook time in minutes.")
    servings: int = Field(description="The number of people this recipe serves.")
    ingredients: List[Ingredient] = Field(description="A detailed list of ingredients with quantities.")
    instructions: List[str] = Field(description="A step-by-step list of clear cooking instructions.")

class SimilarRecipes(BaseModel):
    """A list of titles for recipes similar to the current one, including their local names."""
    suggestions: List[str] = Field(description="A list of three unique and engaging recipe titles in **English** that are similar to the current recipe.")
    local_names: List[str] = Field(description="A list of the three corresponding **local names** (e.g., Hindi, Italian, etc.) for the suggested recipes. This list must have the exact same length and order as 'suggestions'.")


# --- Utility Functions ---

def parse_quantity(quantity_str: str):
    """
    Attempts to parse a quantity string into a float and unit.
    Handles simple numbers and fractions (e.g., '1/2', '1.5').
    """
    quantity_str = quantity_str.strip().lower()
    
    match = re.match(r'(\d+\s*\d*/\d+|\d*\.\d+|\d+/\d+|\d+)', quantity_str)
    
    if match:
        number_str = match.group(0).strip()
        unit_str = quantity_str[len(number_str):].strip()

        if ' ' in number_str and '/' in number_str:
            parts = number_str.split()
            whole = float(parts[0])
            numerator, denominator = map(int, parts[1].split('/'))
            quantity = whole + (numerator / denominator)
        elif '/' in number_str:
            numerator, denominator = map(int, number_str.split('/'))
            quantity = numerator / denominator
        else:
            try:
                quantity = float(number_str)
            except ValueError:
                return None, quantity_str
        
        return quantity, unit_str
    
    return None, quantity_str

def format_scaled_quantity(number, unit_str):
    """Formats a scaled float back into a human-readable string (e.g., '1.5' -> '1 1/2')."""
    if number is None:
        return unit_str
    
    decimal = number - int(number)
    
    if decimal == 0.0:
        formatted_num = str(int(number))
    elif abs(decimal - 0.5) < 0.01:
        formatted_num = f"{int(number) if int(number) > 0 else ''} 1/2".strip()
    elif abs(decimal - 0.25) < 0.01:
        formatted_num = f"{int(number) if int(number) > 0 else ''} 1/4".strip()
    elif abs(decimal - 0.75) < 0.01:
        formatted_num = f"{int(number) if int(number) > 0 else ''} 3/4".strip()
    else:
        formatted_num = f"{number:.2f}" 

    return f"{formatted_num} {unit_str}".strip()

# --- 2. LLM API Interaction (LangChain) ---

def initialize_llm():
    """Initializes the ChatOpenAI model."""
    apiKey = os.getenv("OPENAI_API_KEY", "")
    if not apiKey:
        st.error("Error: OpenAI API Key not found. Please set the OPENAI_API_KEY environment variable.")
        return None
    
    return ChatOpenAI( 
        model="gpt-4o-mini",
        temperature=0.8,
        api_key=apiKey
    )

def generate_recipe_from_llm(ingredients, cuisine, complexity, diet_preference):
    """Calls the LLM API to generate the main structured recipe."""
    llm = initialize_llm()
    if not llm: return None 
    
    diet_instruction = ""
    if diet_preference == "Vegetarian":
        diet_instruction = (
            "You MUST adhere to strict vegetarian protocol. **The recipe and all its ingredients MUST contain absolutely NO meat, poultry, fish, seafood, or animal derived gelatin.** Only plant-based ingredients and dairy/eggs (since eggs are a user input, they are explicitly allowed if provided). If the user provided a non-vegetarian ingredient (like 'chicken') but selected 'Vegetarian', you MUST ignore the non-veg ingredient and substitute it with a plant-based alternative (like 'paneer' or 'tofu') appropriate for the cuisine, and mention the substitution in the recipe description."
        )

    try:
        structured_llm = llm.with_structured_output(Recipe)

        system_prompt = (
            "You are 'Sous Chef AI', an expert culinary assistant specialized in providing "
            "perfectly structured, organized, and detailed recipes. "
            "Your task is to generate a complete, authentic, and delicious recipe based on the user's input. "
            "Crucially, all steps in the **instructions list must be highly detailed, precise, and verbose**, "
            "including specific temperature settings, pan sizes (if applicable), visual cues, and exact timing "
            "where possible. Avoid vague terms like 'cook until done.' "
            "You MUST return the response in the specified JSON format as defined by the provided Pydantic schema. "
            "Provide the estimated Total Calories (kcal) per serving. "
            "Ensure all fields are filled."
            f"\n{diet_instruction}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """
            Please generate one complete recipe.
            - MAIN INGREDIENTS: {ingredients}
            - CUISINE: {cuisine}
            - COOKING SKILL LEVEL: {complexity}
            - DIETARY PREFERENCE: {diet_preference}

            Ensure the recipe is creative, feasible, and uses the main ingredients provided while strictly adhering to the dietary preference.
            """)
        ])
        
        chain = prompt | structured_llm
        
        status_placeholder = st.empty()
        with status_placeholder:
            st.info("Sous Chef AI is expertly planning your meal...")
            start_time = time.time()
            
            recipe_object = chain.invoke({
                "ingredients": ingredients,
                "cuisine": cuisine,
                "complexity": complexity,
                "diet_preference": diet_preference
            })
            
            end_time = time.time()
            
        status_placeholder.success("Recipe generated! Ready for your kitchen.") 
        
        return recipe_object.model_dump()
            
    except (OutputParserException, ValidationError) as e:
        st.error(f"LangChain failed to parse the structured output into the Recipe format. Error: {e}")
        return None
    except Exception as e:
        st.error(f"An API or network error occurred during LangChain invocation. Please check your connection or key. Error: {e}")
        return None

def generate_similar_recipes(current_name, ingredients, cuisine, diet_preference):
    """
    Calls the LLM API to generate suggestions for similar recipes.
    Suggestions are constrained by cuisine and diet.
    """
    llm = initialize_llm()
    if not llm: return None

    diet_constraint = ""
    if diet_preference == "Vegetarian":
        diet_constraint = "All suggested recipes MUST be strictly vegetarian."
    
    try:
        structured_llm = llm.with_structured_output(SimilarRecipes)

        system_prompt = (
            "You are a creative recipe curator. Your task is to suggest three unique recipe titles "
            "that are similar in style or ingredients to the recipe provided. "
            "Crucially, **all three suggestions must belong to the same cuisine** as specified. "
            "For each suggested English title, you must also provide its **local name** or the most common native name. "
            "Do NOT suggest the same recipe title that is provided. "
            f"{diet_constraint} "
            "You MUST return the response in the specified JSON format."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"""
            The current recipe is '{current_name}'.
            - Main Ingredients: {ingredients}
            - CUISINE: {cuisine}
            - DIETARY PREFERENCE: {diet_preference}

            Suggest three similar recipes from the **{cuisine}** cuisine, ensuring they are **{diet_preference}** appropriate.
            """)
        ])
        
        chain = prompt | structured_llm
        
        suggestions_object = chain.invoke({})
        
        return {
            'suggestions': suggestions_object.suggestions,
            'local_names': suggestions_object.local_names
        }
            
    except Exception as e:
        print(f"Error generating similar recipes: {e}")
        return None

# --- Utility Function for Download Feature ---

def format_recipe_for_download(recipe_data):
    """Formats the recipe data into a readable text string."""
    text = f"--- RECIPE: {recipe_data['name'].upper()} ---\n\n"
    text += f"Description: {recipe_data.get('description', 'N/A')}\n"
    text += f"Category: {recipe_data.get('category', 'N/A')}\n"
    text += f"Calories Per Serving: {recipe_data.get('total_calories_kcal', 'N/A')} kcal\n"
    text += f"Historical Fact: {recipe_data.get('historical_fact', 'N/A')}\n"
    text += f"Nutritional Tip: {recipe_data.get('nutritional_tip', 'N/A')}\n"
    text += f"Time: {recipe_data['prep_time_minutes']} minutes\n"
    text += f"Servings: {recipe_data['servings']}\n"
    text += "\n--- INGREDIENTS ---\n"
    for item in recipe_data['ingredients']:
        text += f"- {item['quantity']} of {item['item']}\n"
    text += "\n--- INSTRUCTIONS ---\n"
    for i, step in enumerate(recipe_data['instructions']):
        text += f"{i+1}. {step}\n"
    return text


# --- 3. Streamlit UI and Logic ---

st.set_page_config(layout="wide", page_title="Sous Chef AI: Recipe Curator")

st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    h1 {
        color: #1f77b4;
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #333;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .similar-recipe-button button {
        background-color: #f0f2f6; /* Light gray background */
        color: #1f77b4; /* Blue text */
        border: 1px solid #dcdcdc; 
        font-size: 0.9rem;
        padding: 8px 15px;
        margin-right: 10px;
        margin-bottom: 10px;
        transition: background-color 0.3s;
    }
    .similar-recipe-button button:hover {
        background-color: #e6e8eb;
        color: #0c4b6e;
    }
    .local-name {
        font-size: 0.8rem;
        font-style: italic;
        color: #666;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    /* Add style to ensure radio buttons display vertically in the sidebar */
    .stRadio div {
        display: flex;
        flex-direction: column;
    }
    .stRadio div label {
        margin-bottom: 5px; /* Add some space between options */
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🔪 Sous Chef AI: Recipe Curator")
st.caption("Your intelligent culinary assistant")

# --- Session State Initialization and Pre-Rendering Logic ---

# Initialize session state variables with default values
if 'original_recipe_data' not in st.session_state:
    st.session_state['original_recipe_data'] = None
if 'ingredients_input' not in st.session_state:
    st.session_state['ingredients_input'] = "eggs, flour"
if 'cuisine_select' not in st.session_state:
    st.session_state['cuisine_select'] = 'Indian'
if 'complexity_select' not in st.session_state:
    st.session_state['complexity_select'] = 'Easy (Quick & simple)' 
# Default serving to 2
if 'serving_slider' not in st.session_state:
    st.session_state['serving_slider'] = 2
if 'diet_preference' not in st.session_state:
    st.session_state['diet_preference'] = 'Any'

if 'temp_query' not in st.session_state:
    st.session_state['temp_query'] = None
if 'temp_cuisine' not in st.session_state: 
    st.session_state['temp_cuisine'] = None
if 'similar_recipes' not in st.session_state:
    st.session_state['similar_recipes'] = {'suggestions': [], 'local_names': []}


ingredients_display_value = st.session_state['ingredients_input']

# --- CRITICAL FIX: Pre-update the text area's key before it's drawn ---
if st.session_state['temp_query'] is not None:
    ingredients_display_value = st.session_state['temp_query']
    st.session_state['ingredients_input'] = st.session_state['temp_query'] 
    st.session_state['cuisine_select'] = st.session_state['temp_cuisine']
    
    st.session_state['temp_query'] = None 
    st.session_state['temp_cuisine'] = None 
    
    st.session_state['trigger_suggestion_generation'] = True


# --- Sidebar for User Inputs ---
with st.sidebar:
    
    st.header("What's in your pantry?")
    
    ingredients_input = st.text_area(
        "List your main ingredients (e.g., chicken breast, canned tomatoes, basil):",
        value=ingredients_display_value, 
        height=100,
        key='ingredients_input' 
    )
    
    st.header("Recipe Preferences")
    
    diet_options = ['Any', 'Vegetarian', 'Non-Vegetarian']
    try:
        default_diet_index = diet_options.index(st.session_state['diet_preference'])
    except ValueError:
        default_diet_index = 0
        
    # --- CHANGE: Replaced st.selectbox with st.radio for Dietary Preference ---
    diet_preference = st.radio(
        "Dietary Preference:", 
        diet_options, 
        index=default_diet_index, 
        key='diet_preference'
    )
    # --- END CHANGE ---
    
    cuisine_options = [
        'Any', 'Italian', 'Mexican', 'Indian', 'Chinese', 'Japanese', 
        'Thai', 'French', 'Spanish', 'Greek', 'American', 'German', 
        'Vietnamese', 'Korean', 'Brazilian', 'Moroccan', 'Ethiopian'
    ]
    
    try:
        default_cuisine_index = cuisine_options.index(st.session_state['cuisine_select'])
    except ValueError:
        default_cuisine_index = 0
        
    cuisine_select = st.selectbox("Preferred Cuisine:", cuisine_options, index=default_cuisine_index, key='cuisine_select')
    
    complexity_options = ['Easy (Quick & simple)', 'Medium (Some technique required)', 'Hard (Chef-level challenge)']
    
    try:
        default_complexity_index = complexity_options.index(st.session_state['complexity_select'])
    except ValueError:
        default_complexity_index = 0
        
    complexity_select = st.selectbox("Skill Level:", complexity_options, index=default_complexity_index, key='complexity_select')
    
    generate_button = st.button("✨ Ask Sous Chef AI", use_container_width=True)


# --- Main Content Area ---

# Check if a new generation should be triggered
trigger_generation = generate_button or st.session_state.get('trigger_suggestion_generation', False)
st.session_state['trigger_suggestion_generation'] = False # Reset the flag immediately

if trigger_generation or st.session_state['original_recipe_data']:
    
    if trigger_generation:
        if not st.session_state.get('ingredients_input'):
            st.error("Please enter at least one main ingredient to generate a recipe.")
            st.session_state['original_recipe_data'] = None
            st.stop()
            
        recipe_data = generate_recipe_from_llm(
            st.session_state['ingredients_input'], 
            st.session_state['cuisine_select'], 
            st.session_state['complexity_select'],
            st.session_state['diet_preference']
        )
        
        if recipe_data:
            st.session_state['original_recipe_data'] = recipe_data
            st.session_state['original_ingredients'] = st.session_state['ingredients_input']
            st.session_state['original_cuisine'] = st.session_state['cuisine_select']
            
            if 'serving_slider' not in st.session_state:
                st.session_state['serving_slider'] = recipe_data['servings']
                
            suggestions_data = generate_similar_recipes(
                recipe_data['name'], 
                st.session_state['original_ingredients'], 
                st.session_state['original_cuisine'],
                st.session_state['diet_preference']
            )
            
            if suggestions_data:
                st.session_state['similar_recipes'] = suggestions_data
            else:
                st.session_state['similar_recipes'] = {'suggestions': [], 'local_names': []}
        else:
            st.stop()


    if st.session_state['original_recipe_data']:
        original_data = st.session_state['original_recipe_data']
        original_servings = original_data['servings']
        
        st.markdown(f"## {original_data['name']}")
        st.caption(f"**Category:** {original_data.get('category', 'N/A')} | **Cuisine:** {st.session_state.get('original_cuisine', 'N/A')} | **Diet:** {st.session_state.get('diet_preference', 'Any')}")
        st.info(f"**Summary:** {original_data.get('description', 'A delicious meal.')}")
        
        # --- FIX: Read the current slider value for display and scaling ---
        new_servings = st.session_state.get('serving_slider', original_servings) 
        
        if 'total_calories_kcal' in original_data and original_data['total_calories_kcal'] is not None:
            scaled_calories = int(original_data['total_calories_kcal'] * (original_servings / new_servings)) 
        else:
            scaled_calories = 'N/A'

        # --- METADATA ROW ---
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f'<div class="section-header">⏱️ Total Time</div>', unsafe_allow_html=True)
            st.metric(label="Minutes", value=f"{original_data['prep_time_minutes']} min")
        
        with col2:
            st.markdown(f'<div class="section-header">🍽️ Serves</div>', unsafe_allow_html=True)
            # --- APPLIED FIX: Display the current slider value (new_servings) ---
            st.metric(label="Current Serving", value=f"{new_servings} people")
            # --- END FIX ---

        with col3:
            st.markdown(f'<div class="section-header">🔥 Calories</div>', unsafe_allow_html=True)
            st.metric(label="Per Serving (kcal)", value=f"{scaled_calories}")
            
        with col4:
            st.markdown(f'<div class="section-header">🔪 Complexity</div>', unsafe_allow_html=True)
            st.metric(label="Level", value=st.session_state.get('complexity_select', 'Medium').split(' ')[0])
        
        with col5:
            st.markdown(f'<div class="section-header">💡 Nutritional Tip</div>', unsafe_allow_html=True)
            st.caption(original_data.get('nutritional_tip', 'Enjoy responsibly!'))

        st.divider()

        # --- RECIPE SCALING FEATURE UI ---
        st.markdown("### 👨‍👩‍👧‍👦 Adjust Servings")
        
        # NOTE: This uses the 'serving_slider' key initialized above (default 2)
        new_servings = st.slider(
            'Scale the recipe to serve:',
            min_value=1,
            max_value=12,
            value=st.session_state['serving_slider'], # Use the key's current value
            step=1,
            key='serving_slider' 
        )
        
        scaling_factor = new_servings / original_servings
        
        if new_servings != original_servings:
             st.warning(f"💡 Scaling Factor: **{(scaling_factor):.2f}**. All quantities and the calorie count have been adjusted for **{new_servings} servings**.")
             
             if original_data.get('total_calories_kcal') is not None:
                 updated_scaled_calories = int(original_data['total_calories_kcal'] * (original_servings / new_servings))
                 col_cal_update = st.columns(5)[2]
                 with col_cal_update:
                     st.metric(label="Per Serving (kcal)", value=f"{updated_scaled_calories}")
                 
        else:
             st.success(f"Serving the original **{original_servings}** people.")
        
        st.divider()
        
        # --- Ingredients and Instructions Columns ---
        col_i, col_s = st.columns([1, 2])
        
        with col_i:
            st.markdown("### 🛒 Ingredients")
            
            ingredient_list_markdown = ""
            for item in original_data['ingredients']:
                original_quantity_str = item['quantity']
                
                quantity, unit_str = parse_quantity(original_quantity_str)
                
                if quantity is not None and scaling_factor != 1.0:
                    scaled_quantity = quantity * scaling_factor
                    display_quantity_str = format_scaled_quantity(scaled_quantity, unit_str)
                else:
                    display_quantity_str = original_quantity_str

                ingredient_list_markdown += f"- **{item['item']}**: {display_quantity_str}\n"
            
            st.markdown(ingredient_list_markdown)
        
        with col_s:
            st.markdown("### 📝 Instructions")
            
            instruction_list_markdown = ""
            for i, step in enumerate(original_data['instructions']):
                instruction_list_markdown += f"{i+1}. {step}\n"
            
            st.markdown(instruction_list_markdown)

        st.divider()
        
        # --- Historical Fact at the end ---
        st.markdown(f"**📜 Historical Fact:** *{original_data.get('historical_fact', 'No interesting fact found for this dish.')}*")
        st.divider()
        
        # --- Similar Recipes Feature Display with Local Names ---
        suggestions = st.session_state['similar_recipes'].get('suggestions', [])
        local_names = st.session_state['similar_recipes'].get('local_names', [])
        
        if suggestions:
            st.markdown("### 🔍 Similar Recipes You Might Like")
            
            num_suggestions = min(len(suggestions), len(local_names))
            col_sug = st.columns(num_suggestions)
            
            def update_temp_query(new_query, cuisine):
                """Callback function to safely update temporary keys and trigger rerun."""
                st.session_state['temp_query'] = new_query
                st.session_state['temp_cuisine'] = cuisine

            current_cuisine = st.session_state.get('original_cuisine', 'Any')
            
            for i in range(num_suggestions):
                suggestion_name = suggestions[i]
                local_name = local_names[i]
                
                with col_sug[i]:
                    st.markdown(f'<div class="similar-recipe-button">', unsafe_allow_html=True)
                    st.button(
                        suggestion_name, 
                        key=f"sug_btn_{i}",
                        on_click=update_temp_query,
                        args=(suggestion_name, current_cuisine)
                    )
                    st.markdown(f'<p class="local-name">({local_name})</p>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")

        # --- Download Feature ---
        recipe_text = format_recipe_for_download(original_data)
        
        st.download_button(
            label="⬇️ Download Original Recipe (TXT)",
            data=recipe_text,
            file_name=f"{original_data['name'].replace(' ', '_').lower()}_original.txt",
            mime="text/plain",
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("Built with LangChain and the precision of **Sous Chef AI**.")


# --- Initial State / Placeholder ---
else:
    st.info("Enter your available ingredients and preferences in the sidebar and click '✨ Ask Sous Chef AI' to begin!")
