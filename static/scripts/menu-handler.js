class HeaderMenuManager {
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
      // Continue without auth manager - menu will still work
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
    } else if (this.logoutBtn) {
      // Fallback logout handler if AuthManager is not available
      this.logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        // Simple logout - redirect to home or login page
        window.location.href = '/';
      });
    }
  }

  // Toggle mobile menu
  setupMenuToggle() {
    if (this.menuToggle && this.navMenu) {
      this.menuToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this.navMenu.classList.toggle('show');
      });
    }
  }

  // Toggle profile dropdown
  setupProfileDropdown() {
    if (this.profileButton && this.profileMenu) {
      this.profileButton.addEventListener('click', (e) => {
        e.stopPropagation();
        this.profileMenu.classList.toggle('show');
        
        // Close mobile menu if open
        if (this.navMenu && this.navMenu.classList.contains('show')) {
          this.navMenu.classList.remove('show');
        }
      });

      // Close dropdown if clicked outside
      document.addEventListener('click', (e) => {
        if (
          !this.profileButton.contains(e.target) &&
          !this.profileMenu.contains(e.target)
        ) {
          this.profileMenu.classList.remove('show');
        }
        
        // Also close mobile menu if clicked outside
        if (
          this.navMenu &&
          !this.menuToggle.contains(e.target) &&
          !this.navMenu.contains(e.target)
        ) {
          this.navMenu.classList.remove('show');
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

  // Handle window resize to close mobile menu
  setupWindowResize() {
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768) {
        // Close mobile menu on desktop
        if (this.navMenu && this.navMenu.classList.contains('show')) {
          this.navMenu.classList.remove('show');
        }
      }
    });
  }

  // Setup keyboard navigation
  setupKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
      // Close dropdowns on Escape key
      if (e.key === 'Escape') {
        if (this.profileMenu && this.profileMenu.classList.contains('show')) {
          this.profileMenu.classList.remove('show');
          this.profileButton.focus();
        }
        if (this.navMenu && this.navMenu.classList.contains('show')) {
          this.navMenu.classList.remove('show');
          this.menuToggle.focus();
        }
      }
    });
  }

  // Initialize everything when DOM is ready
  init() {
    // Check if DOM is already loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        this.setupAll();
      });
    } else {
      this.setupAll();
    }
  }

  async setupAll() {
    this.setupMenuToggle();
    this.setupProfileDropdown();
    this.setupWindowResize();
    this.setupKeyboardNavigation();
    await this.initializeAuth();
    this.checkAuthOnLoad();
  }
}

// Instantiate and run the header menu manager
const headerMenuManager = new HeaderMenuManager();
headerMenuManager.init();