// Ask some frontend furu later on to look at it

// Function to update AI message avatars based on theme
function updateAIAvatars() {
  const isDark = document.documentElement.classList.contains('dark');
  const iconSrc = isDark ? '/public/ai-dark-theme.svg' : '/public/ai-light-theme.svg';

  // Target AI message avatars using alt attribute or src
  document.querySelectorAll('img[alt="Avatar for Assistant"], img[alt="Avatar for assistant"], img[src*="avatars/Assistant"]').forEach(img => {
    img.src = iconSrc;
  });
}

// Function to manage copy buttons
function manageCopyButtons() {
  // Remove copy buttons from system messages (token elements)
  document.querySelectorAll('[data-step-type="assistant_message"]').forEach(step => {
    if (step.querySelector('img[alt="Avatar for system"]')) {
      // It's a system message, remove all copy buttons
      step.querySelectorAll('.lucide-copy').forEach(button => {
        const container = button.closest('.flex.items-center');
        if (container) {
          container.remove();
        } else {
          button.remove();
        }
      });
    }
  });

  // Add copy buttons to human and AI messages if not present
  document.querySelectorAll('[data-step-type="user_message"], [data-step-type="assistant_message"]').forEach(step => {
    if (!step.querySelector('img[alt="Avatar for system"]')) {
      // It's human or AI message
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
            setTimeout(() => {
              button.innerHTML = originalHTML;
            }, 2000);
          } catch (err) {
            console.error('Failed to copy text: ', err);
          }
        };
        messageWrapper.parentElement.appendChild(button);
      }
    }
  });
}

// Run on DOM content loaded
document.addEventListener('DOMContentLoaded', () => {
  updateAIAvatars();
  manageCopyButtons();
});
// Also run after a short delay to catch dynamically loaded elements
setTimeout(() => {
  updateAIAvatars();
  manageCopyButtons();
}, 1000);

// Continuously manage copy buttons to handle dynamically added ones, needed to override chainlit wanting to attach it to the token message
setInterval(() => {
  manageCopyButtons();
}, 100);

// Observe theme changes (Chainlit may toggle the 'dark' class)
const themeObserver = new MutationObserver(updateAIAvatars);
themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

// Observe for new elements
const bodyObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.tagName === 'IMG' && (node.alt === 'Avatar for Assistant' || node.alt === 'Avatar for assistant' || node.src.includes('avatars/Assistant'))) {
          updateAIAvatars();
        } else {
          // Check descendants
          node.querySelectorAll && node.querySelectorAll('img[alt="Avatar for Assistant"], img[alt="Avatar for assistant"], img[src*="avatars/Assistant"]').forEach(img => {
            updateAIAvatars();
          });
        }
        // Check for new copy buttons
        if (node.matches && node.matches('.lucide-copy')) {
          const step = node.closest('[data-step-type]');
          if (step && step.getAttribute('data-step-type') === 'assistant_message' && step.querySelector('img[alt="Avatar for system"]')) {
            const container = node.closest('.flex.items-center');
            if (container) {
              container.remove();
            }
          }
        }
        // Check for new messages
        if (node.matches && (node.matches('[data-step-type="user_message"]') || node.matches('[data-step-type="assistant_message"]'))) {
          manageCopyButtons();
        } else if (node.querySelectorAll) {
          node.querySelectorAll('[data-step-type="user_message"], [data-step-type="assistant_message"]').forEach(() => {
            manageCopyButtons();
          });
        }
      }
    });
  });
});
bodyObserver.observe(document.body, { childList: true, subtree: true });
