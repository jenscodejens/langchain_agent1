// Function to update avatars based on theme for both Assistant and Tools
function updateAvatars() {
  const isDark = document.documentElement.classList.contains('dark');

  // Define mapping for authors and their corresponding theme icons
  const avatarMap = {
    'Assistant': {
      dark: '/public/avatars/ai-dark-theme.svg',
      light: '/public/avatars/ai-light-theme.svg'
    },
    'Tools': {
      dark: '/public/avatars/tools-dark-theme.svg',
      light: '/public/avatars/tools-light-theme.svg'
    },
    'tool': {
      dark: '/public/avatars/tools-dark-theme.svg',
      light: '/public/avatars/tools-light-theme.svg'
    }
  };

  Object.keys(avatarMap).forEach(author => {
    const iconSrc = isDark ? avatarMap[author].dark : avatarMap[author].light;

    // Select images by alt text (case insensitive) or partial src path
    const selector = `
      img[alt*="Avatar for ${author}" i],
      img[alt="${author}" i],
      img[src*="avatars/${author}"]
    `;

    document.querySelectorAll(selector).forEach(img => {
      if (img.src !== iconSrc) {
        img.src = iconSrc;
      }
    });
  });
}

// Initial Run
document.addEventListener('DOMContentLoaded', () => {
  updateAvatars();
});

// Observe theme changes
const themeObserver = new MutationObserver(updateAvatars);
themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

// Observe for new elements
const bodyObserver = new MutationObserver((mutations) => {
  updateAvatars();
});
bodyObserver.observe(document.body, { childList: true, subtree: true });
