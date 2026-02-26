// Utility functions for AI Newsletter

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-TW', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  });
}

function highlightQuery(text, query) {
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

// 設置導航欄活躍狀態
function setActiveNav() {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-links a');
  
  navLinks.forEach(link => {
    link.classList.remove('active');
    if (currentPath.includes(link.getAttribute('href').split('/').pop())) {
      link.classList.add('active');
    }
  });
}

document.addEventListener('DOMContentLoaded', setActiveNav);

// 可重複使用的卡片展開/收起邏輯
function setupToggleButtons() {
  const toggleButtons = document.querySelectorAll('.toggle-btn');
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      const summary = this.previousElementSibling;
      const isHidden = summary.style.display === 'none';
      summary.style.display = isHidden ? 'block' : 'none';
      this.textContent = isHidden ? '收起' : '展開';
    });
  });
}