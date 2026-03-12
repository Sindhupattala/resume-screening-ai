export class AuthManager {
  constructor() {
    this.menuToggle = document.getElementById("menu-toggle");
    this.navMenu = document.getElementById("nav-menu");
    this.loginForm = document.querySelector("form");
    this.usernameInput = document.getElementById("username");
    this.passwordInput = document.getElementById("password");
    this.loginBtn = document.getElementById("login-btn");

    this.init();
  }

  init() {
    this.setupEventListeners();
  }

  setupEventListeners() {
    if (this.menuToggle && this.navMenu) {
      this.menuToggle.addEventListener("click", () => {
        this.navMenu.classList.toggle("hidden");
        this.navMenu.classList.toggle("flex");
        this.navMenu.classList.toggle("flex-col");
        this.navMenu.classList.toggle("absolute");
        this.navMenu.classList.toggle("top-14");
        this.navMenu.classList.toggle("right-4");
        this.navMenu.classList.toggle("bg-white");
        this.navMenu.classList.toggle("p-4");
        this.navMenu.classList.toggle("rounded-lg");
        this.navMenu.classList.toggle("shadow-lg");
      });
    }

    if (this.loginForm) {
      this.loginForm.addEventListener("submit", (e) => this.handleLogin(e));
    }
  }

  showLoadingState() {
    if (this.loginBtn) {
      this.loginBtn.classList.add("loading");
      this.loginBtn.disabled = true;
      this.loginBtn.innerHTML = `
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Logging in...
      `;
    }
  }

  hideLoadingState() {
    if (this.loginBtn) {
      this.loginBtn.classList.remove("loading");
      this.loginBtn.disabled = false;
      this.loginBtn.textContent = "Log in";
    }
  }

  addErrorStyles(inputElement) {
    if (inputElement) {
      inputElement.classList.add("shake", "border-red-500");
      setTimeout(() => {
        inputElement.classList.remove("shake");
      }, 300);
    }
  }

  clearErrors() {
    [this.usernameInput, this.passwordInput].forEach((input) => {
      if (input) input.classList.remove("shake", "border-red-500");
    });
    const existingErrors = this.loginForm.querySelectorAll(".error-message");
    existingErrors.forEach((error) => error.remove());
  }

  validateInputs() {
    let isValid = true;

    if (!this.usernameInput?.value.trim()) {
      this.addErrorStyles(this.usernameInput);
      isValid = false;
    }

    if (!this.passwordInput?.value) {
      this.addErrorStyles(this.passwordInput);
      isValid = false;
    }

    return isValid;
  }

  async handleLogin(e) {
    e.preventDefault();
    this.clearErrors();

    if (!this.validateInputs()) return;

    this.showLoadingState();

    const formData = new URLSearchParams();
    formData.append("grant_type", "password");
    formData.append("username", this.usernameInput.value.trim());
    formData.append("password", this.passwordInput.value);
    formData.append("scope", "");
    formData.append("client_id", "string");
    formData.append("client_secret", "");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      const responseText = await response.text();
      let result;

      try {
        result = responseText ? JSON.parse(responseText) : {};
      } catch (jsonError) {
        console.error("Failed to parse JSON response:", responseText);
        throw new Error("Invalid server response format");
      }

      if (!response.ok) {
        let errorMessage = "Login failed";

        if (result.detail) {
          errorMessage = Array.isArray(result.detail)
            ? result.detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
            : result.detail;
        } else if (result.message) {
          errorMessage = result.message;
        } else if (result.error) {
          errorMessage = result.error;
        } else if (typeof result === "string") {
          errorMessage = result;
        } else if (typeof result === "object") {
          errorMessage = JSON.stringify(result);
        }

        throw new Error(errorMessage);
      }

      if (result.access_token) {
        this.storeTokens(result);
        this.setupAutoLogout(); // Set auto logout timer
        this.setupAutoRefreshToken(); // Optional: auto-refresh before expiry
        window.location.href = "/ui/dashboard";
      } else {
        throw new Error("Authentication failed: No access token received");
      }
    } catch (error) {
      console.error("Login error:", error);
      this.showError(error.message || "Something went wrong. Please try again.");
    } finally {
      this.hideLoadingState();
    }
  }

  showError(message) {
    const errorElement = document.createElement("div");
    errorElement.className =
      "error-message text-red-500 text-sm mt-2 text-center";
    errorElement.textContent = message;

    this.loginBtn.insertAdjacentElement("afterend", errorElement);

    setTimeout(() => {
      if (errorElement.parentNode) {
        errorElement.parentNode.removeChild(errorElement);
      }
    }, 5000);
  }

  storeTokens(tokens) {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    localStorage.setItem("token_type", tokens.token_type);

    // Use token's `expires_in` or default to 2 hours = 7200 seconds
    const expiresIn = tokens.expires_in || 7200;
    const expirationTime = Date.now() + expiresIn * 1000;
    localStorage.setItem("token_expiration", expirationTime.toString());
  }

  getAccessToken() {
    return localStorage.getItem("access_token");
  }

  getRefreshToken() {
    return localStorage.getItem("refresh_token");
  }

  getTokenType() {
    return localStorage.getItem("token_type");
  }

  isTokenExpired() {
    const expiration = localStorage.getItem("token_expiration");
    if (!expiration) return true;

    return Date.now() > parseInt(expiration, 10);
  }

  isAuthenticated() {
    return !!this.getAccessToken() && !this.isTokenExpired();
  }

  clearTokens() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("token_type");
    localStorage.removeItem("token_expiration");
  }

  async refreshToken() {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const formData = new URLSearchParams();
    formData.append("grant_type", "refresh_token");
    formData.append("refresh_token", refreshToken);
    formData.append("client_id", "string");

    try {
      const response = await fetch("/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error("Token refresh failed");
      }

      if (result.access_token) {
        this.storeTokens(result);
        this.setupAutoLogout(); // Reset auto-logout timer
        return result.access_token;
      } else {
        throw new Error("No new access token received");
      }
    } catch (error) {
      console.error("Refresh token error:", error);
      this.logout();
      throw error;
    }
  }

  async logout() {
      const accessToken = this.getAccessToken();
      
      try {
        // Try with empty body first (many logout endpoints don't need a body)
        const response = await fetch("/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${accessToken}`,
            // Include only Content-Type if needed
            // "Content-Type": "application/json",
          },
          // Remove body completely if not needed
          // body: JSON.stringify({ refresh_token: this.getRefreshToken() }),
        });

        if (!response.ok) {
          console.warn("Logout API returned non-OK status:", response.status);
        }
      } catch (err) {
        console.warn("Logout API failed (non-critical):", err);
      }

      // Always clear local tokens and redirect
      this.clearTokens();
      window.location.href = "/";
    }
  setupAutoLogout() {
    const expiration = localStorage.getItem("token_expiration");
    if (!expiration) return;

    const now = Date.now();
    const timeUntilLogout = parseInt(expiration, 10) - now;

    if (timeUntilLogout > 0) {
      setTimeout(() => {
        this.logout();
        alert("You've been logged out due to session expiration.");
      }, timeUntilLogout);
    }
  }

  setupAutoRefreshToken() {
    const expiration = localStorage.getItem("token_expiration");
    if (!expiration) return;

    const now = Date.now();
    const timeUntilLogout = parseInt(expiration, 10) - now;

    // Refresh token 5 minutes before it expires
    const refreshTimeout = timeUntilLogout - 5 * 60 * 1000;

    if (refreshTimeout > 0) {
      setTimeout(async () => {
        try {
          await this.refreshToken();
        } catch (err) {
          console.error("Failed to auto-refresh token:", err);
        }
      }, refreshTimeout);
    }
  }

  checkAutoLogoutOnLoad() {
    if (this.isAuthenticated()) {
      this.setupAutoLogout();
      this.setupAutoRefreshToken();
    } else {
      this.logout();
    }
  }
}