// Function to update AI message avatars based on theme
function updateAIAvatars() {
  const isDark = document.documentElement.classList.contains('dark');
  const iconSrc = isDark ? '/public/ai-dark-theme.svg' : '/public/ai-light-theme.svg';

  // Target AI message avatars using alt attribute or src
  document.querySelectorAll('img[alt="Avatar for Assistant"], img[src*="avatars/Assistant"]').forEach(img => {
    img.src = iconSrc;
  });
}

// Run on page load
updateAIAvatars();
// Also run after a short delay to catch dynamically loaded elements
setTimeout(() => {
  updateAIAvatars();
}, 1000);

// Observe theme changes (Chainlit may toggle the 'dark' class)
const themeObserver = new MutationObserver(updateAIAvatars);
themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

// Observe for new img elements and update if they are avatars
const bodyObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.tagName === 'IMG' && (node.alt === 'Avatar for Assistant' || node.src.includes('avatars/Assistant'))) {
          updateAIAvatars();
        } else {
          // Check descendants
          node.querySelectorAll && node.querySelectorAll('img[alt="Avatar for Assistant"], img[src*="avatars/Assistant"]').forEach(img => {
            updateAIAvatars();
          });
        }
      }
    });
  });
});
bodyObserver.observe(document.body, { childList: true, subtree: true });
