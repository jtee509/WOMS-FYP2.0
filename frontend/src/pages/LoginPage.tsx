import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import { useAuth } from '../contexts/AuthContext';

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
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#1A1A2E',
        p: 2,
      }}
    >
      <Card
        sx={{
          display: 'flex',
          maxWidth: 900,
          width: '100%',
          minHeight: 540,
          borderRadius: 3,
          overflow: 'hidden',
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        }}
      >
        {/* ---- LEFT SIDE: Decorative panel ---- */}
        <Box
          sx={{
            width: '45%',
            display: { xs: 'none', md: 'flex' },
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: '#16213E',
          }}
        >
          {/* Large primary blob */}
          <Box
            sx={{
              position: 'absolute',
              width: 240,
              height: 240,
              borderRadius: '50%',
              background:
                'linear-gradient(135deg, #1565C0 0%, #1E88E5 100%)',
              opacity: 0.7,
              top: '10%',
              left: '5%',
              filter: 'blur(2px)',
            }}
          />
          {/* Secondary orange blob */}
          <Box
            sx={{
              position: 'absolute',
              width: 180,
              height: 180,
              borderRadius: '50%',
              background:
                'linear-gradient(135deg, #FF8F00 0%, #FFA726 100%)',
              opacity: 0.55,
              bottom: '15%',
              right: '0%',
              filter: 'blur(2px)',
            }}
          />
          {/* Dark accent blob */}
          <Box
            sx={{
              position: 'absolute',
              width: 140,
              height: 140,
              borderRadius: '50%',
              background:
                'linear-gradient(135deg, #0D47A1 0%, #1565C0 100%)',
              opacity: 0.5,
              top: '40%',
              left: '30%',
              filter: 'blur(1px)',
            }}
          />
          {/* Small light accent */}
          <Box
            sx={{
              position: 'absolute',
              width: 80,
              height: 80,
              borderRadius: '50%',
              background:
                'linear-gradient(135deg, #FFA726 0%, #FF8F00 100%)',
              opacity: 0.45,
              top: '20%',
              right: '20%',
              filter: 'blur(1px)',
            }}
          />
          {/* Tiny primary dot */}
          <Box
            sx={{
              position: 'absolute',
              width: 50,
              height: 50,
              borderRadius: '50%',
              background:
                'linear-gradient(135deg, #1E88E5 0%, #0D47A1 100%)',
              opacity: 0.6,
              bottom: '8%',
              left: '15%',
              filter: 'blur(1px)',
            }}
          />
        </Box>

        {/* ---- RIGHT SIDE: Login form ---- */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            p: { xs: 3, sm: 5 },
            backgroundColor: '#FFFFFF',
          }}
        >
          {/* WOMS branding */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <WarehouseIcon
              sx={{ fontSize: 36, color: '#1565C0' }}
            />
            <Typography
              variant="h4"
              sx={{ fontWeight: 700, color: '#1565C0' }}
            >
              WOMS
            </Typography>
          </Box>
          <Typography
            variant="body2"
            sx={{ color: '#555770', mb: 4 }}
          >
            Warehouse Order Management System
          </Typography>

          {/* Welcome heading */}
          <Typography
            variant="h5"
            sx={{ fontWeight: 600, color: '#1A1A2E', mb: 3 }}
          >
            Welcome Back!
          </Typography>

          {/* Error alert */}
          {error && (
            <Alert
              severity="error"
              sx={{ mb: 2 }}
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          {/* Login form */}
          <Box component="form" onSubmit={handleSubmit} noValidate>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={emailError}
              helperText={
                emailError
                  ? 'Please enter a valid email address'
                  : emailTouched && emailValid
                    ? 'Perfect!'
                    : ' '
              }
              slotProps={{
                formHelperText: {
                  sx: {
                    color:
                      emailTouched && emailValid ? 'success.main' : undefined,
                  },
                },
              }}
              margin="normal"
              autoComplete="email"
              autoFocus
            />

            <TextField
              fullWidth
              label="Password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              helperText=" "
              margin="normal"
              autoComplete="current-password"
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                        aria-label={
                          showPassword ? 'Hide password' : 'Show password'
                        }
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              color="primary"
              disabled={!canSubmit}
              sx={{ mt: 2, mb: 2, py: 1.3, fontSize: '1rem' }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Sign In'
              )}
            </Button>
          </Box>

          {/* Secondary links */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mt: 1,
            }}
          >
            <Button
              variant="text"
              size="small"
              sx={{
                color: '#555770',
                textTransform: 'none',
                fontWeight: 400,
              }}
            >
              Forgot My Password
            </Button>
            <Button
              variant="text"
              size="small"
              sx={{
                color: '#1565C0',
                textTransform: 'none',
                fontWeight: 500,
              }}
            >
              Request An Account
            </Button>
          </Box>
        </Box>
      </Card>
    </Box>
  );
}
