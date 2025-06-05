// public/js/script.js
document.getElementById('symptom-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const symptoms = document.getElementById('symptoms-input').value;
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptoms })
    });
    const result = await response.json();
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = `
      <h2>Analysis Result for: "${symptoms}"</h2>
      ${result.initial_statement ? `<p class="initial-statement">${result.initial_statement}</p>` : ''}
      ${result.possible_causes ? `
        <div class="diagnosis-section">
          <h3>Possible Causes</h3>
          ${result.possible_causes.map(c => `
            <div class="diagnosis-card">
              <div class="diagnosis-card-title">${c.title}</div>
              <div class="diagnosis-card-description">${c.description}</div>
            </div>
          `).join('')}
        </div>` : ''}
      ${result.immediate_attention_points ? `
        <div class="diagnosis-section">
          <h3 class="important-notice">Seek Immediate Medical Attention If:</h3>
          <ul class="diagnosis-list">
            ${result.immediate_attention_points.map(p => `<li>${p}</li>`).join('')}
          </ul>
        </div>` : ''}
      ${result.conclusion ? `
        <div class="diagnosis-section conclusion-text">
          <h4>Conclusion</h4>
          <p>${result.conclusion}</p>
        </div>` : ''}
    `;
  });