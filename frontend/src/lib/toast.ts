export function showToast(message: string, type: 'success' | 'error' = 'error') {
  const id = 'global-toast-container';
  let container = document.getElementById(id) as HTMLDivElement | null;
  if (!container) {
    container = document.createElement('div');
    container.id = id;
    Object.assign(container.style, {
      position: 'fixed',
      right: '16px',
      bottom: '16px',
      zIndex: '9999',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end',
      pointerEvents: 'none',
    } as Partial<CSSStyleDeclaration>);
    document.body.appendChild(container);
  }

  const el = document.createElement('div');
  el.textContent = message;
  Object.assign(el.style, {
    marginTop: '8px',
    padding: '10px 14px',
    borderRadius: '8px',
    color: '#fff',
    backgroundColor: type === 'success' ? '#16a34a' : '#dc2626',
    boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
    pointerEvents: 'auto',
    opacity: '1',
    transition: 'opacity 0.4s ease, transform 0.35s ease',
    transform: 'translateY(0px)'
  } as Partial<CSSStyleDeclaration>);

  container.appendChild(el);

  // Auto remove
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(6px)';
    setTimeout(() => el.remove(), 450);
  }, 3000);
}
