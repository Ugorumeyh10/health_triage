// api/analyze.js
import fetch from 'node-fetch';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { symptoms } = req.body;
  try {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama3-8b-8192',
        messages: [
          { role: 'system', content: 'You are a helpful and accurate medical triage assistant.' },
          { role: 'user', content: `Here are the symptoms: ${symptoms}. What could this indicate and what should the patient do next?` }
        ]
      })
    });

    if (!response.ok) {
      throw new Error(`Groq API returned status ${response.status}`);
    }

    const result = await response.json();
    const ai_text_content = result.choices?.[0]?.message?.content || 'No content returned';

    // Simplified parsing (adapt parse_ai_response_to_structured_data if needed)
    const parsed_data = {
      initial_statement: `Analyzing symptoms: ${symptoms}`,
      possible_causes: [
        { title: 'Possible Cause', description: ai_text_content }
      ],
      immediate_attention_points: ['Seek help if symptoms are severe'],
      conclusion: 'Consult a healthcare professional'
    };

    res.status(200).json({ symptoms, result: parsed_data });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}