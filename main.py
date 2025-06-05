from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import httpx
import os
from dotenv import load_dotenv
import re

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def parse_ai_response_to_structured_data(text: str) -> dict:
    """
    Parses the AI's textual response into a structured dictionary.
    This parser is based on the observed structure of the AI's output.
    """
    parsed_data = {
        "initial_statement": "",
        "possible_causes_intro": "",
        "possible_causes": [],
        "next_steps_intro": "",
        "immediate_attention_header": "",
        "immediate_attention_points": [],
        "other_steps_header": "",
        "other_steps": [],
        "conclusion": ""
    }

    if not text or not isinstance(text, str):
        return parsed_data # Return empty structure if text is invalid or not a string

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    idx = 0

    # Helper to consume lines until a non-empty line or end of lines
    def consume_empty_lines():
        nonlocal idx
        while idx < len(lines) and not lines[idx]:
            idx += 1

    # Initial statement
    if idx < len(lines) and not re.match(r"^(Based on your report|1\.|\* |\*\*|What should the patient do next\?)", lines[idx], re.IGNORECASE):
        parsed_data["initial_statement"] = lines[idx]
        idx += 1
        consume_empty_lines()

    # Possible causes intro
    if idx < len(lines) and "possible causes to consider" in lines[idx].lower():
        parsed_data["possible_causes_intro"] = lines[idx]
        idx += 1
        consume_empty_lines()

    # Possible causes list
    stop_phrases_causes = ("what should the patient do next?", "**seek immediate medical attention**", "**otherwise, take these steps**", "remember, it's always better")
    while idx < len(lines):
        match = re.match(r"^\d+\.\s*\*\*(.*?)\*\*:\s*(.*)", lines[idx])
        if match:
            title = match.group(1).strip()
            description = match.group(2).strip()
            temp_idx = idx + 1
            while temp_idx < len(lines) and not re.match(r"^\d+\.\s", lines[temp_idx]) and not lines[temp_idx].lower().startswith(stop_phrases_causes):
                description += " " + lines[temp_idx]
                temp_idx += 1
            parsed_data["possible_causes"].append({"title": title, "description": description.strip()})
            idx = temp_idx
        else:
            break
    consume_empty_lines()

    # Next steps intro
    if idx < len(lines) and "what should the patient do next?" in lines[idx].lower():
        parsed_data["next_steps_intro"] = lines[idx]
        idx += 1
        consume_empty_lines()

    # Immediate attention header & points
    if idx < len(lines) and lines[idx].lower().startswith("**seek immediate medical attention** if:"):
        parsed_data["immediate_attention_header"] = lines[idx] # Keep full header for now
        idx += 1
        consume_empty_lines()
        while idx < len(lines) and lines[idx].startswith("* "):
            parsed_data["immediate_attention_points"].append(lines[idx][2:])
            idx += 1
        consume_empty_lines()
            
    # Other steps header & points
    if idx < len(lines) and lines[idx].lower().startswith("**otherwise, take these steps**:"):
        parsed_data["other_steps_header"] = lines[idx] # Keep full header
        idx += 1
        consume_empty_lines()
        stop_phrases_other_steps = ("remember, it's always better",)
        while idx < len(lines):
            match = re.match(r"^\d+\.\s*\*\*(.*?)\*\*:\s*(.*)", lines[idx])
            if match:
                title = match.group(1).strip()
                description = match.group(2).strip()
                temp_idx = idx + 1
                while temp_idx < len(lines) and not re.match(r"^\d+\.\s", lines[temp_idx]) and not lines[temp_idx].lower().startswith(stop_phrases_other_steps):
                    description += " " + lines[temp_idx]
                    temp_idx += 1
                parsed_data["other_steps"].append({"title": title, "description": description.strip()})
                idx = temp_idx
            else:
                break
        consume_empty_lines()

    # Conclusion
    if idx < len(lines):
        parsed_data["conclusion"] = " ".join(lines[idx:])

    return parsed_data

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_symptoms(request: Request, symptoms: str = Form(...)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192", # Or any other currently supported model from Groq
                "messages": [
                    {"role": "system", "content": "You are a helpful and accurate medical triage assistant."},
                    {"role": "user", "content": f"Here are the symptoms: {symptoms}. What could this indicate and what should the patient do next?"}
                ]
            }
        )

        ai_text_content = None
        error_message_for_template = "Error: Could not retrieve analysis. Please check server logs." # Default

        # For debugging: print status and try to parse JSON
        print(f"Groq API Status Code: {response.status_code}")
        try:
            result = response.json()
            print(f"Groq API Response: {result}")
        except httpx.JSONDecodeError as e: # More specific exception
            print(f"Failed to parse Groq API response as JSON: {e}. Response text: {response.text}")
            print(f"Groq API Response Text: {response.text}")
            result = None # Ensure result is None if JSON parsing fails
            error_message_for_template = f"Error: Could not parse AI response (Status: {response.status_code}). Details: {response.text[:200]}..."

        if response.status_code == 200 and result:
            try:
                choices = result.get("choices")
                if choices and isinstance(choices, list) and len(choices) > 0:
                    message = choices[0].get("message")
                    if message and isinstance(message, dict):
                        ai_text_content = message.get("content")
                        if not ai_text_content:
                            print("Error: 'content' key missing or empty in Groq response message.")
                            error_message_for_template = "Error: AI response format is invalid (missing content)."
                            ai_text_content = None # Ensure it's None
                        else:
                            error_message_for_template = None # Clear default error if content is found
                    else:
                        print("Error: 'message' key missing or not a dict in Groq response choices[0].")
                        error_message_for_template = "Error: AI response format is invalid (missing message)."
                else:
                    print("Error: 'choices' key missing, not a list, or empty in Groq response.")
                    error_message_for_template = "Error: AI did not provide any choices in the response."
            except Exception as e: # Catch any other unexpected errors during parsing
                print(f"An unexpected error occurred while parsing Groq response: {e}")
                error_message_for_template = "Error: Failed to parse AI response structure."
        elif result and "error" in result: # If Groq returned a JSON error object
            error_message_from_api = result.get("error", {}).get("message", "Unknown API error")
            error_message_for_template = f"Error from AI assistant: {error_message_from_api} (Status: {response.status_code})"
        elif response.status_code != 200:
            error_message_for_template = f"Error: AI assistant API returned status {response.status_code}. Response: {response.text[:200]}..."

        # Prepare data for the template
        template_data_to_render = error_message_for_template

        if ai_text_content: # If we successfully got content from AI
            parsed_data = parse_ai_response_to_structured_data(ai_text_content)
            # Check if parsing yielded meaningful structured data
            is_meaningful_parse = any(
                parsed_data.get(key) for key in ["possible_causes", "immediate_attention_points", "other_steps"] if parsed_data.get(key)
            )
            if is_meaningful_parse:
                template_data_to_render = parsed_data
            else: # Parsing wasn't meaningful, fall back to raw text
                template_data_to_render = ai_text_content

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": template_data_to_render,
        "symptoms": symptoms
    })