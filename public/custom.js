// Function to update avatars based on theme for both Assistant and Tools
function updateAvatars() {
  const isDark = document.documentElement.classList.contains('dark');
  
  // Define mapping for authors and their corresponding theme icons
  const avatarMap = {
    'Assistant': {
      dark: '/public/ai-dark-theme.svg',
      light: '/public/ai-light-theme.svg'
    },
    'Tools': {
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

// Function to manage copy buttons
function manageCopyButtons() {
  // Remove copy buttons from system messages (token elements)
  document.querySelectorAll('[data-step-type="assistant_message"]').forEach(step => {
    if (step.querySelector('img[alt*="system" i]')) {
      step.querySelectorAll('.lucide-copy').forEach(button => {
        const container = button.closest('.flex.items-center');
        if (container) container.remove();
        else button.remove();
      });
    }
  });

  // Add copy buttons to human and AI messages if not present
  document.querySelectorAll('[data-step-type="user_message"], [data-step-type="assistant_message"]').forEach(step => {
    // Don't add to system or tools messages
    const isSystem = step.querySelector('img[alt*="system" i]');
    const isTool = step.querySelector('img[alt*="tools" i]');
    
    if (!isSystem && !isTool) {
      const messageWrapper = step.querySelector('div[id^="step-"]');
      if (messageWrapper && !messageWrapper.parentElement.querySelector('.copy-button')) {
        const button = document.createElement('button');
        button.className = 'copy-button inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground h-9 w-9 text-muted-foreground';
        if (step.getAttribute('data-step-type') === 'user_message') {
          button.classList.add('ml-auto');
        }
        button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-copy h-4 w-4" aria-hidden="true"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>';
        button.onclick = async () => {
          const messageContent = step.querySelector('.message-content');
          const text = messageContent ? messageContent.textContent.trim() : '';
          try {
            await navigator.clipboard.writeText(text);
            const originalHTML = button.innerHTML;
            button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check h-4 w-4" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>';
            setTimeout(() => { button.innerHTML = originalHTML; }, 2000);
          } catch (err) { console.error('Failed to copy text: ', err); }
        };
        messageWrapper.parentElement.appendChild(button);
      }
    }
  });
}

// Initial Run
document.addEventListener('DOMContentLoaded', () => {
  updateAvatars();
  manageCopyButtons();
});

// Continuously manage copy buttons
setInterval(manageCopyButtons, 500);

// Observe theme changes
const themeObserver = new MutationObserver(updateAvatars);
themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

// Observe for new elements
const bodyObserver = new MutationObserver((mutations) => {
  updateAvatars();
  manageCopyButtons();
});
bodyObserver.observe(document.body, { childList: true, subtree: true });
