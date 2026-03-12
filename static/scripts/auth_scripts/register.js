class SignupForm {
  constructor(formId) {
    this.form = document.getElementById(formId);
    this.firstName = document.getElementById('first_name');
    this.lastName = document.getElementById('last_name');
    this.username = document.getElementById('username');
    this.email = document.getElementById('email');
    this.password = document.getElementById('password');
    this.confirmPassword = document.getElementById('confirm_password');
    this.terms = document.getElementById('terms');
    this.signupBtn = document.getElementById('signup-btn');
    this.btnText = document.getElementById('btn-text');
    this.spinner = document.getElementById('spinner');
    
    // API configuration
    this.API_URL = '/auth/signup';
    
    this.init();
  }

  init() {
    this.form.addEventListener('submit', this.handleSubmit.bind(this));
  }

  async handleSubmit(e) {
    e.preventDefault();
    
    // Clear previous messages
    this.clearMessages();
    
    // Validate form
    if (!this.validateForm()) {
      return;
    }
    
    // Show loading state
    this.setLoadingState(true);
    
    try {
      // Prepare and send data
      const payload = this.preparePayload();
      const response = await this.sendData(payload);
      
      // Handle success
      this.showSuccessMessage();
      this.redirectAfterDelay('/', 2000);
    } catch (error) {
      this.handleError(error);
    } finally {
      // Reset loading state
      this.setLoadingState(false);
    }
  }

  clearMessages() {
    const existingError = document.querySelector('.error-message');
    if (existingError) existingError.remove();

    const existingSuccess = document.querySelector('.success-message');
    if (existingSuccess) existingSuccess.remove();
  }

  validateForm() {
    // Check required fields
    if (!this.firstName.value.trim() || !this.lastName.value.trim() || 
        !this.username.value.trim() || !this.email.value.trim() || 
        !this.password.value || !this.confirmPassword.value) {
      this.showError('Please fill all required fields.');
      return false;
    }

    // Check terms agreement
    if (!this.terms.checked) {
      this.showError('You must agree to the terms and conditions.');
      return false;
    }

    // Check password length
    if (this.password.value.length < 8) {
      this.showError('Password must be at least 8 characters.');
      this.addErrorStyles(this.password);
      return false;
    }

    // Check password match
    if (this.password.value !== this.confirmPassword.value) {
      this.showError('Passwords do not match.');
      this.addErrorStyles(this.password);
      this.addErrorStyles(this.confirmPassword);
      return false;
    }

    return true;
  }

  preparePayload() {
    return {
      first_name: this.firstName.value.trim(),
      last_name: this.lastName.value.trim(),
      username: this.username.value.trim(),
      email: this.email.value.trim(),
      password: this.password.value
    };
  }

  async sendData(payload) {
    const response = await fetch(this.API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Failed to create account');
    }

    return data;
  }

  setLoadingState(isLoading) {
    this.signupBtn.disabled = isLoading;
    this.btnText.textContent = isLoading ? 'Creating account...' : 'Create Account';
    this.spinner.classList.toggle('hidden', !isLoading);
  }

  showError(message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message mt-2 p-3 bg-red-50 text-red-600 text-sm rounded-lg';
    errorElement.innerHTML = `
      <div class="flex items-center">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span>${message}</span>
      </div>
    `;

    this.signupBtn.insertAdjacentElement('afterend', errorElement);

    setTimeout(() => {
      if (errorElement.parentNode) {
        errorElement.classList.add('opacity-0', 'transition-opacity', 'duration-300');
        setTimeout(() => {
          errorElement.parentNode.removeChild(errorElement);
        }, 300);
      }
    }, 5000);
  }

  showSuccessMessage() {
    const successElement = document.createElement('div');
    successElement.className = 'success-message mt-2 p-3 bg-green-50 text-green-600 text-sm rounded-lg';
    successElement.innerHTML = `
      <div class="flex items-center">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span>Account created successfully! Redirecting...</span>
      </div>
    `;

    this.signupBtn.insertAdjacentElement('afterend', successElement);
  }

  addErrorStyles(inputElement) {
    if (!inputElement) return;
    
    inputElement.classList.add('border-red-500', 'shake');
    setTimeout(() => {
      inputElement.classList.remove('shake');
    }, 400);
  }

  redirectAfterDelay(url, delay) {
    setTimeout(() => {
      window.location.href = url;
    }, delay);
  }
}

// Initialize the form when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new SignupForm('signup-form');
});