async function sendMessage(){
  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if(!text) return;
  appendMessage('user', text);
  input.value = '';
  const res = await fetch('/api/chat', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: text})
  });
  const data = await res.json();
  appendMessage('bot', data.reply);
}

function appendMessage(role, text){
  const box = document.getElementById('chat-box');
  const p = document.createElement('div');
  p.className = 'message ' + role;
  p.innerText = text;
  box.appendChild(p);
  box.scrollTop = box.scrollHeight;
}

async function saveMood(){
  const mood = document.getElementById('mood-select').value;
  const note = document.getElementById('mood-note').value;
  if(!mood) return alert('Choose a mood first');
  await fetch('/api/mood', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({mood: mood, note: note})
  });
  document.getElementById('mood-note').value = '';
  document.getElementById('mood-select').value = '';
  loadMoods();
}

async function loadMoods(){
  const res = await fetch('/api/mood_history');
  const items = await res.json();
  const list = document.getElementById('mood-list');
  list.innerHTML = '';
  items.forEach(it => {
    const li = document.createElement('li');
    const d = new Date(it.created_at);
    li.innerText = `${it.mood} — ${it.note || ''} (${d.toLocaleString()})`;
    list.appendChild(li);
  });
}

// load initial moods on page load
window.addEventListener('load', ()=>{
  if(document.getElementById('mood-list')) loadMoods();
});
