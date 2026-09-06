/* ========================================
   CASAMENTO VICTOR & LARISSA - SCRIPTS
   ======================================== */

// ─── Lista de presentes (com humor!) ────────────────────────────────────────
const presentes = [
  { id: 1,  emoji: '🚗', nome: 'Peça Aleatória do Fusca',             descricao: 'Pode ser qualquer coisa. O motor já é Subaru, vai que é o carburador?',         valor: 'R$ 150' },
  { id: 2,  emoji: '🪗', nome: 'Afinador de Sanfona Profissional',    descricao: 'A Larissa garante que a sanfona não precisa afinar. A gente sabe.',               valor: 'R$ 160' },
  { id: 3,  emoji: '🏐', nome: 'Bola de Futevôlei Oficial',           descricao: 'Para o Victor chutar bonito e fingir que é profissional na praia.',               valor: 'R$ 180' },
  { id: 4,  emoji: '🧘', nome: 'Tapete de Yoga de Luxo',              descricao: 'Ela já tem um, mas esse tem memória de postura e zero julgamento.',               valor: 'R$ 320' },
  { id: 5,  emoji: '🎸', nome: 'Corda de Violão (pacote com 6)',      descricao: 'Porque sempre quebra uma na hora errada — e nunca é pouco.',                      valor: 'R$ 200' },
  { id: 6,  emoji: '🧠', nome: 'Livro: "Como Conviver com um Fusca"', descricao: 'Manual de sobrevivência emocional escrito especialmente para a Larissa.',          valor: 'R$ 150' },
  { id: 7,  emoji: '🚴', nome: 'Selim de Bike Ergonômico',            descricao: 'Para o Victor fazer pedal sem reclamar das dores nos próximos 3 dias.',            valor: 'R$ 280' },
  { id: 8,  emoji: '🏋️', nome: 'Mensalidade de Academia (6 meses)',   descricao: 'A Larissa vai todo dia. O Victor disse que começa na segunda — há 3 anos.',       valor: 'R$ 600' },
  { id: 9,  emoji: '⚽', nome: 'Chuteira Society do Victor',          descricao: 'Ele JURA que com chuteira nova fica 30% melhor no campo.',                         valor: 'R$ 450' },
  { id: 10, emoji: '📚', nome: 'Curso Online de Psicologia Positiva', descricao: 'Para a Larissa ajudar os clientes — e ocasionalmente o Victor.',                   valor: 'R$ 480' },
  { id: 11, emoji: '🔧', nome: 'Kit Ferramentas para o Fusca',        descricao: 'Para quando o fusca "resolver" parar no meio do caminho. De novo.',               valor: 'R$ 380' },
  { id: 12, emoji: '💆', nome: 'Dia de Spa Completo',                 descricao: 'Porque cuidar dos outros o dia todo exige cuidar de si também.',                  valor: 'R$ 550' },
  { id: 13, emoji: '🐶', nome: 'Plano de Saúde Pet da Luana',         descricao: 'Ela manda na casa. Ela manda no coração. Ela merece o melhor plano.',              valor: 'R$ 350' },
];

// ─── Renderiza os cards de presentes ────────────────────────────────────────
function renderizarPresentes() {
  const grid = document.getElementById('presentesGrid');
  grid.innerHTML = presentes.map(p => `
    <div class="presente-card">
      <div class="presente-img-wrap">${p.emoji}</div>
      <div class="presente-info">
        <div class="presente-nome">${p.nome}</div>
        <div class="presente-descricao">${p.descricao}</div>
        <div class="presente-valor">${p.valor}</div>
        <button class="presente-btn" onclick="abrirPagamento(${p.id})">Presentear 💚</button>
      </div>
    </div>
  `).join('');
}

// ─── Abre modal da lista ─────────────────────────────────────────────────────
function abrirListaPresentes() {
  renderizarPresentes();
  document.getElementById('modalLista').classList.add('ativo');
  document.body.style.overflow = 'hidden';
}

function fecharListaPresentes() {
  document.getElementById('modalLista').classList.remove('ativo');
  document.body.style.overflow = '';
}

// ─── Abre modal do Pix para o presente escolhido ────────────────────────────
function abrirPagamento(id) {
  const p = presentes.find(x => x.id === id);
  if (!p) return;

  document.getElementById('modalPagamentoConteudo').innerHTML = `
    <span class="pix-presente-emoji">${p.emoji}</span>
    <div class="pix-presente-nome">${p.nome}</div>
    <div class="pix-presente-valor">${p.valor}</div>
    <p class="pix-instrucao">Escaneie o QR Code ou copie a chave Pix:</p>
    <div class="qr-code-pix">
      <img src="qrcode.png" alt="QR Code Pix">
    </div>
    <div class="pix-key-box">
      <code>43501942826</code>
      <button class="copy-btn" onclick="copyPix()">Copiar</button>
    </div>
    <br>
    <button class="voltar-lista-btn" onclick="voltarParaLista()">← Voltar à lista</button>
  `;

  document.getElementById('modalLista').classList.remove('ativo');
  document.getElementById('modalPagamento').classList.add('ativo');
}

function fecharPagamento() {
  document.getElementById('modalPagamento').classList.remove('ativo');
  document.body.style.overflow = '';
}

function voltarParaLista() {
  document.getElementById('modalPagamento').classList.remove('ativo');
  document.getElementById('modalLista').classList.add('ativo');
}

// Fecha modal ao clicar fora
function fecharModalSeFora(event) {
  if (event.target === event.currentTarget) {
    fecharListaPresentes();
    fecharPagamento();
    fecharDresscode();
  }
}

// ─── Dress Code popup ────────────────────────────────────────────────────────
function abrirDresscode() {
  document.getElementById('modalDresscode').classList.add('ativo');
  document.body.style.overflow = 'hidden';
}

function fecharDresscode() {
  document.getElementById('modalDresscode').classList.remove('ativo');
  document.body.style.overflow = '';
}

// ─── Countdown ───────────────────────────────────────────────────────────────
function updateCountdown() {
  const wedding = new Date('2027-01-23T17:45:00-03:00').getTime();
  const now = Date.now();
  const diff = wedding - now;

  if (diff <= 0) {
    document.getElementById('countdown').innerHTML =
      '<p style="color:var(--creme);font-size:1.4rem;font-family:\'Cormorant Garamond\',serif">O grande dia chegou! 💍</p>';
    return;
  }

  const dias    = Math.floor(diff / (1000 * 60 * 60 * 24));
  const horas   = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutos = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const segundos= Math.floor((diff % (1000 * 60)) / 1000);

  document.getElementById('dias').textContent    = String(dias).padStart(3, '0');
  document.getElementById('horas').textContent   = String(horas).padStart(2, '0');
  document.getElementById('minutos').textContent = String(minutos).padStart(2, '0');
  document.getElementById('segundos').textContent= String(segundos).padStart(2, '0');
}

setInterval(updateCountdown, 1000);
updateCountdown();

// ─── Nav visível após scroll ─────────────────────────────────────────────────
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('visible', window.scrollY > window.innerHeight * 0.5);
}, { passive: true });

// ─── Reveal ao entrar na viewport ───────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) entry.target.classList.add('visible');
  });
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

// ─── Copiar Pix ──────────────────────────────────────────────────────────────
function copyPix() {
  navigator.clipboard.writeText('43501942826');
  showToast('Pix copiado! 💚');
}

// ─── Copiar Hashtag ──────────────────────────────────────────────────────────
function copyHashtag() {
  navigator.clipboard.writeText('#VictorELarissa2027');
  showToast('Hashtag copiada! 📸');
}

// ─── Toast ───────────────────────────────────────────────────────────────────
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// ─── Lightbox ────────────────────────────────────────────────────────────────
function openLightbox(src) {
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  document.getElementById('lightbox').classList.remove('active');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeLightbox();
    fecharListaPresentes();
    fecharPagamento();
    fecharDresscode();
  }
});
