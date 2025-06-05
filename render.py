# render.py
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('index.html')
mock_data = {
  "symptoms": "fever, cough",
  "result": {
    "initial_statement": "Analyzing symptoms: fever, cough",
    "possible_causes": [
      {"title": "Common Cold", "description": "A viral infection causing fever and cough."}
    ],
    "immediate_attention_points": ["High fever above 103°F"],
    "other_steps": [
      {"title": "Rest", "description": "Get plenty of rest."}
    ],
    "conclusion": "Consult a doctor if symptoms worsen."
  }
}
output = template.render(**mock_data)
with open('public/index.html', 'w') as f:
  f.write(output)