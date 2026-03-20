import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { useAuth } from '../api/contexts/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const emailTouched = email.length > 0;
  const emailValid = emailRegex.test(email);
  const emailError = emailTouched && !emailValid;

  const canSubmit = emailValid && password.length > 0 && !loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
      const from =
        (location.state as { from?: { pathname: string } })?.from?.pathname ||
        '/';
      navigate(from, { replace: true });
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as {
          response?: { data?: { detail?: string } };
        };
        setError(
          axiosErr.response?.data?.detail || 'Login failed. Please try again.',
        );
      } else {
        setError('Unable to connect to server. Please check your connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-login-bg p-2">
      <div className="flex max-w-[900px] w-full min-h-[540px] rounded-card overflow-hidden shadow-login bg-surface">
        {/* ---- LEFT SIDE: Decorative panel ---- */}
        <div className="w-[45%] hidden md:flex items-center justify-center relative overflow-hidden bg-login-panel">
          <div className="login-blob login-blob--primary" />
          <div className="login-blob login-blob--secondary" />
          <div className="login-blob login-blob--dark-accent" />
          <div className="login-blob login-blob--light-accent" />
          <div className="login-blob login-blob--tiny-dot" />
        </div>

        {/* ---- RIGHT SIDE: Login form ---- */}
        <div className="flex-1 flex flex-col justify-center p-6 sm:p-10 bg-surface">
          {/* WOMS branding */}
          <div className="flex items-center gap-2 mb-1">
            <WarehouseIcon className="!text-4xl !text-primary" />
            <h1 className="text-3xl font-bold text-primary">WOMS</h1>
          </div>
          <p className="text-sm text-text-secondary mb-8">
            Warehouse Order Management System
          </p>

          {/* Welcome heading */}
          <h2 className="text-xl font-semibold text-text-primary mb-6">
            Welcome Back!
          </h2>

          {/* Error alert */}
          {error && (
            <div className="flex items-center gap-2 bg-error-bg text-error-text rounded-default px-4 py-3 mb-4 text-sm">
              <span className="flex-1">{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-error-text hover:opacity-70 font-bold text-lg leading-none cursor-pointer"
              >
                &times;
              </button>
            </div>
          )}

          {/* Login form */}
          <form onSubmit={handleSubmit} noValidate>
            {/* Email field */}
            <div className="mb-4">
              <label htmlFor="login-email" className="form-label">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`form-input ${emailError ? 'form-input--error' : ''}`}
                autoComplete="email"
                autoFocus
              />
              <p
                className={`form-helper ${
                  emailError
                    ? 'text-error'
                    : emailTouched && emailValid
                      ? 'text-success'
                      : 'text-transparent'
                }`}
              >
                {emailError
                  ? 'Please enter a valid email address'
                  : emailTouched && emailValid
                    ? 'Perfect!'
                    : '\u00A0'}
              </p>
            </div>

            {/* Password field */}
            <div className="mb-4">
              <label htmlFor="login-password" className="form-label">
                Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input pr-12"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary cursor-pointer"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <VisibilityOff fontSize="small" />
                  ) : (
                    <Visibility fontSize="small" />
                  )}
                </button>
              </div>
              <p className="form-helper text-transparent">&nbsp;</p>
            </div>

            {/* Submit button */}
            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full mt-2 mb-2 py-3 bg-primary hover:bg-primary-dark text-white font-semibold text-base rounded-default shadow-none hover:shadow-button-hover transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {loading ? (
                <span className="inline-block w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Secondary links */}
          <div className="flex justify-between items-center mt-2">
            <button
              type="button"
              className="text-sm text-text-secondary hover:underline cursor-pointer bg-transparent border-none"
            >
              Forgot My Password
            </button>
            <button
              type="button"
              className="text-sm text-primary font-medium hover:underline cursor-pointer bg-transparent border-none"
            >
              Request An Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
