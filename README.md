# 🔪 Sous Chef AI: Structured Recipe Curator

**Sous Chef AI** is an intelligent, interactive web application built with **Streamlit** and **LangChain**. It leverages the power of OpenAI's LLMs to generate high-quality, perfectly structured cooking recipes based on user-defined ingredients, cuisine, and dietary preferences.

The core innovation is using **LangChain's structured output capabilities** combined with **Pydantic schemas** to guarantee the LLM's response is a valid, usable JSON object, making the application robust and reliable.

---

## ✨ Key Features

- **Structured Recipe Output**  
  Uses Pydantic to enforce a strict Recipe data structure, including fields for instructions, ingredients, metadata, and nutritional facts. This eliminates typical LLM output inconsistencies.

- **Dynamic Quantity Scaling**  
  Adjust a slider to change the number of servings. Ingredients are automatically recalculated, intelligently handling fractions and units.

- **Contextual Recipe Suggestions**  
  Generates three similar recipe ideas from the same cuisine, including their local (native) names. Click to generate a new recipe immediately.

- **Enriched Metadata**  
  Each recipe includes a calculated caloric estimate per serving, a historical fact about the dish, and a nutritional tip.

- **User-Friendly UI**  
  Built with Streamlit for a clean, responsive, and intuitive interface.

---

## 🚀 Technologies Used

| Technology   | Purpose                                                        |
|-------------|----------------------------------------------------------------|
| Python      | Core programming language                                       |
| Streamlit   | Creates the responsive, interactive web application frontend   |
| LangChain   | Orchestrates prompt engineering and structured LLM calls       |
| OpenAI      | Provides the gpt-4o-mini model for text generation             |
| Pydantic    | Defines strict data models (schemas) for validated JSON output |
| os, re      | Handles environment variables and regex for quantity parsing  |

---

## ⚙️ Installation and Setup

### 1. Prerequisites
- Python 3.8+
- OpenAI API Key

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/sous-chef-ai.git
cd sous-chef-ai
```
### 3. Create a Virtual Environment and Install Dependencies
```bash
# Create and activate environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install required packages
pip install -r requirements.txt
```
### 4.Configure Your API Key
```bash
# Linux/macOS
export OPENAI_API_KEY='YOUR_OPENAI_KEY_HERE'

# Windows (Command Prompt)
set OPENAI_API_KEY=YOUR_OPENAI_KEY_HERE # Replace YOUR_OPENAI_KEY_HERE with your actual key.
```

### 5.How to Run
```bash
streamlit run main.py
```

### 🍴 Usage Example

- Input Ingredients: In the sidebar, list your ingredients (e.g.,  chicken, mushrooms, cream, pasta).

- Select Preferences: Choose cuisine (e.g., Italian) and skill level (e.g., Medium).

- Generate Recipe: Click the ✨ Ask Sous Chef AI button.

- Interact: A structured recipe appears. Use the "Adjust Servings" slider to scale ingredients from 2 to 12 servings instantly.


### 🛠️ How It Works

![Sous Chef AI Workflow](https://your-image-link-here.com/workflow.png)


1. **User Input:**  
   - Users enter a list of available ingredients in the sidebar.  
   - Optionally, users select cuisine, dietary restrictions, and skill level.

2. **Prompt Processing:**  
   - The input is sent to the **LangChain pipeline**, which structures a prompt for the LLM.  
   - **Pydantic schemas** validate that the output will be in a consistent JSON format.

3. **Recipe Generation:**  
   - OpenAI's **gpt-4o-mini** model generates the recipe based on the structured prompt.  
   - The recipe includes:  
     - Step-by-step cooking instructions  
     - Ingredient list with quantities  
     - Metadata such as estimated calories, historical facts, and nutritional tips  

4. **Dynamic Scaling:**  
   - Users can adjust the **servings slider**, and ingredient quantities are automatically recalculated, intelligently handling fractions and units.

5. **Contextual Suggestions:**  
   - Three similar recipes from the same cuisine are generated for inspiration.  
   - Users can click any suggestion to instantly generate a new recipe.

6. **Interactive UI:**  
   - The recipe, scaling, and suggestions are displayed in a clean, responsive **Streamlit interface**.  
   - Users can interact seamlessly, generating multiple recipes without reloading the app.