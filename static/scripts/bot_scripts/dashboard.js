class HeaderManager {
  constructor() {
    this.authManager = null;
    this.logoutBtn = null;
    this.menuToggle = document.getElementById("menu-toggle");
    this.navMenu = document.getElementById("nav-menu");
    this.profileButton = document.getElementById("profile-menu-button");
    this.profileMenu = document.getElementById("profile-menu");
  }

  // Initialize AuthManager dynamically
  async initializeAuth() {
    try {
      const module = await import('/static/scripts/auth_scripts/auth.js');
      if (module.AuthManager && typeof module.AuthManager === 'function') {
        this.authManager = new module.AuthManager();
        console.log('AuthManager initialized successfully.');
        this.setupLogoutHandler();
      } else {
        console.error('AuthManager is not a valid constructor.');
      }
    } catch (err) {
      console.error('Failed to load AuthManager:', err.message);
    }
  }

  // Setup logout handler
  setupLogoutHandler() {
    this.logoutBtn = document.getElementById('logout-btn');
    if (this.logoutBtn && this.authManager) {
      this.logoutBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        try {
          await this.authManager.logout();
        } catch (err) {
          console.error('Logout failed:', err);
          // Still clear tokens and redirect even if API fails
          this.authManager.clearTokens();
          window.location.href = '/';
        }
      });
    }
  }

  // Toggle mobile menu
  setupMenuToggle() {
    if (this.menuToggle && this.navMenu) {
      this.menuToggle.addEventListener('click', () => {
        this.navMenu.classList.toggle('hidden');
      });
    }
  }

  // Toggle profile dropdown
  setupProfileDropdown() {
    if (this.profileButton && this.profileMenu) {
      this.profileButton.addEventListener('click', () => {
        this.profileMenu.classList.toggle('hidden');
      });

      // Close dropdown if clicked outside
      document.addEventListener('click', (e) => {
        if (
          !this.profileButton.contains(e.target) &&
          !this.profileMenu.contains(e.target)
        ) {
          this.profileMenu.classList.add('hidden');
        }
      });
    }
  }

  // Check auth state on load
  checkAuthOnLoad() {
    if (
      this.authManager &&
      typeof this.authManager.checkAutoLogoutOnLoad === 'function'
    ) {
      this.authManager.checkAutoLogoutOnLoad();
    }
  }

  // Initialize everything when DOM is ready
  init() {
    document.addEventListener('DOMContentLoaded', async () => {
      this.setupMenuToggle();
      this.setupProfileDropdown();
      await this.initializeAuth();
      this.checkAuthOnLoad();
    });
  }
}

// Instantiate and run
const headerManager = new HeaderManager();
headerManager.init();